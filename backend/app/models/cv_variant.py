from typing import Optional
from sqlmodel import SQLModel, Field


class CVVariant(SQLModel, table=True):
    __tablename__ = "cv_variants"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    file_path: str
    focus_tags: str = "[]"  # JSON array stored as text
    is_active: bool = True
