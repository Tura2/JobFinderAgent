from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Company(SQLModel, table=True):
    __tablename__ = "companies"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    website: Optional[str] = None
    ats_type: str  # greenhouse | lever | workday | custom | linkedin
    ats_slug: Optional[str] = None
    linkedin_url: Optional[str] = None
    career_page_url: Optional[str] = None
    active: bool = True
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_test_at: Optional[datetime] = Field(default=None)
    last_test_passed: Optional[bool] = Field(default=None)
    last_test_jobs_found: Optional[int] = Field(default=None)
