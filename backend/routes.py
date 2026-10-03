from database import engine
from datetime import datetime
import os
import logging
import asyncio

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from models import Job, Thumbnail


from services.generator import process_job, STYLE_ORDER
from services.imagekit_service import upload_file, get_varients


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# request response schemas

class CreateJobRequest(BaseModel):
    prompt: str
    num_thumbnails: int
    headshot_url: str

class CreateJobResponse(BaseModel):
    job_id: str


class CreateThumbnailResponse(BaseModel):
    id : str
    style_name : str
    status : str
    image_kit_url : str | None = None
    error_message : str | None = None
    varients : dict | None

class JobResponse(BaseModel):
    id : int
    prompt : str
    num_thumbnails : int
    headshot_url : str
    status : str
    created_at : datetime
    thumbnails : list[CreateThumbnailResponse]


# routes

@router.post("/upload-headshot")
async def upload_headshot(file : UploadFile = File(...)):
    contents = await file.read()
    file_extension = os.path.splitext(file.filename)[1]
    url = upload_file(
        file_bytes=contents,
        file_name=file.filename or "headshot" + file_extension,
        folder="/headshot",
        content_type=file.content_type or "image/png"
    )
    return {"url" : url}


@router.post("/jobs" , response_model=CreateJobResponse)
async def create_job(
    req : CreateJobRequest,
    session : Session = Depends(get_session)
):
  if req.num_thumbnails < 1 or req.num_thumbnails > 3:
    raise HTTPException(status_code=400 , detail="Number of thumbnails must be between 1 and 3")

  if not req.prompt.strip():
    raise HTTPException(status_code=400, detail="Prompt is required")

  job = Job(
    prompt = req.prompt,
    headshot_url = req.headshot_url,
  )
  session.add(job)

  styles_to_use = STYLE_ORDER[:req.num_thumbnails]

  thumbnails = []
  for style_name in styles_to_use:
    thumb = Thumbnail(
        job_id = job.id,
        style_name = style_name,
    )
    session.add(thumb)
    thumbnails.append(thumb)

  session.commit()
  
#   Fire and forgot style generation
  asyncio.create_task(process_job(job.id))
  return CreateJobResponse(job_id = job.id)

    

@router.get("/jobs/{job_id}" , response_model=JobResponse)
async def get_job(
    job_id : int,
    session : Session = Depends(get_session)
):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    thumbnails = session.exec(select(Thumbnail).where(Thumbnail.job_id == job_id)).all()
    return JobResponse(
        id = job.id,
        prompt = job.prompt,
        num_thumbnails = job.num_thumbnails,
        headshot_url = job.headshot_url,
        status = job.status,
        created_at = job.created_at,
        thumbnails = [CreateThumbnailResponse(
            id = t.id,
            style_name = t.style_name,
            status = t.status,
            image_kit_url = t.image_kit_url,
            error_message = t.error_message,
            varients = get_varients(t.image_kit_url) if t.image_kit_url else None,
        ) for t in thumbnails],
    )


@router.get("/jobs{job_id}/stream")
async def stream_job(job_id : str):
    async def event_generator():
        with Session(engine) as session:
            while True:
                job = session.get(Job, job_id)
                if not job:
                    raise HTTPException(status_code=404, detail="Job not found")
                if job.status == "completed":
                    break
                yield f"data: {job.status}\n\n"
                await asyncio.sleep(1)
            yield f"data: {job.status}\n\n"



    




