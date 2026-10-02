import asyncio
import logging

from sqlmodel import Session, select
from database import engine
from models import Job, Thumbnail

from services.openai_service import generate_image
from services.imagekit_service import upload_file

logger = logging.getLogger(__name__)


STYLES = {
    "bold_dramatic" : """Bold and dramatic professionalYouTube Thumbnail, cinematic lighting, high contrast, sharp focus, hyper-detailed, 8k, Ultra HD, professional photo edit, eye-catching composition, rule of thirds, dynamic angle, dramatic shadows, vibrant colors, highly detailed face, 8k resolution, professional studio lighting""",

    "clean_minimal" : """Clean minimal professionalYouTube Thumbnail, bright lighting, soft shadows, balanced composition, modern typography, ample white space, professional color palette, 4k resolution, flat design aesthetic""",

    "vibrant_energetic" : """Vibrant energetic professionalYouTube Thumbnail, bright and saturated colors, high contrast, dynamic composition, bold typography, modern design elements, 4k resolution, eye-catching and lively""",

    "neon_cyberpunk" : """Neon cyberpunk professionalYouTube Thumbnail, cinematic lighting, high contrast, sharp focus, hyper-detailed, 8k, Ultra HD, professional photo edit, eye-catching composition, rule of thirds, dynamic angle, dramatic shadows, vibrant colors, highly detailed face, 8k resolution, professional studio lighting""",
    
    "minimalist_corporate" : """Minimalist corporate professionalYouTube Thumbnail, clean layout, lots of white space, modern typography, subtle shadows, professional color palette, balanced composition, vector art elements, 4k resolution, subtle gradients, corporate branding""",
    
    "watercolor_art" : """Watercolor art professionalYouTube Thumbnail, soft edges, artistic composition, vibrant paint splatters, hand-painted feel, textured paper look, dynamic brush strokes, bright and cheerful colors, 4k resolution, creative illustration style"""
}

STYLE_ORDER = [
    "bold_dramatic",
    "vibrant_energetic",
    "neon_cyberpunk",
    "minimalist_corporate",
    "watercolor_art",
    "clean_minimal"
]

async def generate_single_thumbnail(thumbnail_id : str, prompt: str, headshot_url: str) -> str:
    # DB mark generating
    with Session(engine) as session:
        thumbnail = session.get(Thumbnail, thumbnail_id)
        thumbnail.status = "generating"
        style_name = thumbnail.style_name
        session.add(thumbnail)
        session.commit()
        
    style_prompt = STYLES[style_name]

    try:
        image_bytes = await generate_image(prompt, style_prompt, headshot_url)
        print("Image generated")
        with Session(engine) as session:
            thumbnail = session.get(Thumbnail, thumbnail_id)
            job_id = thumbnail.job_id
        
        url = upload_file(
            file_bytes=image_bytes,
            file_name = f"{thumbnail_id}.png",
            folder=f"/thumbnails/{job_id}",
        )
        
        with Session(engine) as session:
            thumbnail = session.get(Thumbnail, thumbnail_id)
            thumbnail.image_kit_url = url
            thumbnail.status = "uploaded"
            session.add(thumbnail)
            session.commit()
        logger.info(f"Thumbnail {thumbnail_id} uploaded successfully")
        
        
    except Exception as e:
        logger.error(f"Error generating thumbnail {thumbnail_id}: {e}")
        with Session(engine) as session:
            thumbnail = session.get(Thumbnail, thumbnail_id)
            thumbnail.status = "error"
            thumbnail.error_message = str(e)[:100]
            session.add(thumbnail)
            session.commit()
        
    
        
async def process_job(job_id:str):
    with Session(engine) as session:
        job = session.get(Job, job_id)
        job.status = "processing"
        prompt = job.prompt
        headshot_url = job.headshot_url
        session.add(job)
        session.commit()

        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()

    thumbnail_ids = [t.id for t in thumbnails]

    tasks = [generate_single_thumbnail(tid, prompt, headshot_url) for tid in thumbnail_ids]

    # This will run all thumbnails in parallel.
    await asyncio.gather(*tasks, return_exceptions=True)

    with Session(engine) as session:
        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()

        all_failed = all(t.status == "failed" for t in thumbnails)

        job = session.get(Job, job_id)
        job.status = "failed" if all_failed else "completed"
        session.add(job)
        session.commit()

        
    
        
        
    