from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Application(SQLModel, table=True):
    __tablename__ = "applications"

    id: Optional[int] = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="matches.id")
    cv_variant_id: int = Field(foreign_key="cv_variants.id")
    ats_url: Optional[str] = None
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None
    notes: Optional[str] = None
    outcome_status: str = "pending"  # pending | interview | offer | rejected
    last_status_update: Optional[datetime] = None
