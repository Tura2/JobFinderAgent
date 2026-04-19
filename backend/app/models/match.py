from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Match(SQLModel, table=True):
    __tablename__ = "matches"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id")
    score: int
    reasoning: str
    cv_variant_id: Optional[int] = Field(default=None, foreign_key="cv_variants.id")
    status: str = "new"  # low_match|new|reviewed|skipped|applied|rejected|no_response|interview|offer
    matched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    telegram_message_id: Optional[int] = Field(default=None)
