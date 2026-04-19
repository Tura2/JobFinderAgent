from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    title: str
    url: str
    description_raw: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None
    source: str  # ats_api | scrapling | linkedin
    content_hash: str = Field(unique=True)
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
