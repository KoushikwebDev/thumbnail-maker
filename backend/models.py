from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from sqlmodel import Field, SQLModel, Relationship


def _uuid4() -> str:
    return str(uuid4())

def _now() -> datetime:
    return datetime.now(tz=timezone.utc)

# create model

class Thumbnail(SQLModel, table=True):
    id: str = Field(default_factory=_uuid4, primary_key=True)

    job_id: str = Field(foreign_key="job.id")
    # Every Thumbnail belongs to a Job.
    
    style_name: str = Field(default="")
    status: str = Field(default="pending")
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_now)

    job: Optional["Job"] = Relationship(back_populates="thumbnails")


class Job(SQLModel, table=True):
    id: str = Field(default_factory=_uuid4, primary_key=True)
    prompt: str = Field(default="")
    num_thumbnails: int = Field(default=1, ge=1, le=10) # ge = greater than equal, le = less than equal
    headshot_url: Optional[str] = Field(default="")
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=_now)

    thumbnails: List[Thumbnail] = Relationship(back_populates="job")