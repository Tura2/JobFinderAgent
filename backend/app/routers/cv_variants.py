from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.cv_variant import CVVariant

router = APIRouter()


class CVVariantCreate(BaseModel):
    name: str
    file_path: str
    focus_tags: str = "[]"


@router.get("")
async def list_cv_variants(session: Session = Depends(get_session)):
    return list(session.exec(select(CVVariant).where(CVVariant.is_active == True)).all())


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_cv_variant(body: CVVariantCreate, session: Session = Depends(get_session)):
    cv = CVVariant(**body.model_dump())
    session.add(cv)
    session.commit()
    session.refresh(cv)
    return cv


@router.delete("/{variant_id}")
async def deactivate_cv_variant(variant_id: int, session: Session = Depends(get_session)):
    cv = session.get(CVVariant, variant_id)
    if not cv:
        raise HTTPException(status_code=404, detail="CV variant not found")

    cv.is_active = False
    session.add(cv)
    session.commit()
    return {"deactivated": True, "id": variant_id}
