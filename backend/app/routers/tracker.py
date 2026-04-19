from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import verify_token
from app.database import get_session
from app.models.application import Application
from app.models.match import Match
from app.models.job import Job
from app.models.company import Company

router = APIRouter(dependencies=[Depends(verify_token)])


class ApplicationUpdate(BaseModel):
    outcome_status: Optional[str] = None
    notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None


@router.get("/tracker")
async def get_tracker(session: Session = Depends(get_session)):
    results = session.exec(
        select(Application, Match, Job, Company)
        .join(Match, Application.match_id == Match.id)
        .join(Job, Match.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .order_by(Application.applied_at.desc())
    ).all()

    return [
        {
            "id": app.id,
            "match_id": app.match_id,
            "outcome_status": app.outcome_status,
            "notes": app.notes,
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "confirmed_at": app.confirmed_at.isoformat() if app.confirmed_at else None,
            "job_title": job.title,
            "company_name": company.name,
            "score": match.score,
        }
        for app, match, job, company in results
    ]


@router.patch("/applications/{app_id}")
async def update_application(
    app_id: int,
    body: ApplicationUpdate,
    session: Session = Depends(get_session),
):
    app = session.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(app, key, value)

    app.last_status_update = datetime.now(timezone.utc)
    session.add(app)
    session.commit()
    session.refresh(app)
    return app
