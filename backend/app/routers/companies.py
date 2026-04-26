from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.company import Company

router = APIRouter()


class CompanyCreate(BaseModel):
    name: str
    website: Optional[str] = None
    ats_type: str
    ats_slug: Optional[str] = None
    linkedin_url: Optional[str] = None
    career_page_url: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    ats_type: Optional[str] = None
    ats_slug: Optional[str] = None
    linkedin_url: Optional[str] = None
    career_page_url: Optional[str] = None
    active: Optional[bool] = None


@router.get("")
async def list_companies(session: Session = Depends(get_session)):
    return list(session.exec(select(Company)).all())


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_company(body: CompanyCreate, session: Session = Depends(get_session)):
    company = Company(**body.model_dump())
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


@router.patch("/{company_id}")
async def update_company(company_id: int, body: CompanyUpdate, session: Session = Depends(get_session)):
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(company, key, value)

    session.add(company)
    session.commit()
    session.refresh(company)
    return company


@router.delete("/{company_id}")
async def delete_company(company_id: int, session: Session = Depends(get_session)):
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    session.delete(company)
    session.commit()
    return {"deleted": True, "id": company_id}
