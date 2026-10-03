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

    

    



    




