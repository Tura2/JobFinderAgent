from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode, urlparse, urlunparse

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models.company import Company
from app.models.job import Job
from app.models.match import Match
from app.models.cv_variant import CVVariant
from app.models.application import Application

router = APIRouter()


# --- Helpers ---

def build_ats_apply_url(job_url: str, ats_type: str) -> str:
    first = settings.applicant_first_name
    last = settings.applicant_last_name
    email = settings.applicant_email
    linkedin = settings.applicant_linkedin_url
    portfolio = settings.applicant_portfolio_url

    params: dict = {}
    if ats_type == "greenhouse":
        params = {
            "first_name": first, "last_name": last, "email": email,
            "linkedin_profile": linkedin, "website": portfolio,
        }
    elif ats_type == "lever":
        params = {
            "name": f"{first} {last}".strip(), "email": email,
            "urls[LinkedIn]": linkedin, "urls[Portfolio]": portfolio,
        }

    if not params:
        return job_url

    parsed = urlparse(job_url)
    qs = {k: v for k, v in params.items() if v}
    return urlunparse(parsed._replace(query=urlencode(qs)))


# --- Response schemas ---

class JobOut(BaseModel):
    id: int
    title: str
    url: str
    description_raw: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None


class CompanyOut(BaseModel):
    id: int
    name: str
    website: Optional[str] = None


class CVVariantOut(BaseModel):
    id: int
    name: str
    file_path: str
    focus_tags: str = "[]"


class MatchListItem(BaseModel):
    id: int
    score: int
    reasoning: str
    status: str
    matched_at: datetime
    job_title: str
    company_name: str


class ScoreBreakdown(BaseModel):
    tech_stack: int
    role_type: int
    domain: int
    seniority: int
    location: int


class MatchDetail(BaseModel):
    id: int
    score: int
    reasoning: str
    status: str
    matched_at: datetime
    reviewed_at: Optional[datetime] = None
    score_breakdown: Optional[ScoreBreakdown] = None
    job: JobOut
    company: CompanyOut
    cv_variant: Optional[CVVariantOut] = None
    ambiguous_variants: list[CVVariantOut] = []
    ats_url: str = ""


class ApplyRequest(BaseModel):
    ats_url: Optional[str] = None
    chosen_cv_variant_id: Optional[int] = None


class ApplyResponse(BaseModel):
    match: MatchListItem
    application: dict
    ats_url: str


# --- Endpoints ---

@router.get("", response_model=list[MatchListItem])
async def get_pending_matches(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    from fastapi import Response
    from sqlmodel import func

    total = session.exec(
        select(func.count()).select_from(Match).where(Match.status == "new")
    ).one()
    matches = session.exec(
        select(Match, Job, Company)
        .join(Job, Match.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(Match.status == "new")
        .order_by(Match.score.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    from fastapi.responses import JSONResponse
    items = [
        MatchListItem(
            id=m.id, score=m.score, reasoning=m.reasoning, status=m.status,
            matched_at=m.matched_at, job_title=j.title, company_name=c.name,
        ).model_dump(mode="json")
        for m, j, c in matches
    ]
    return JSONResponse(content=items, headers={"X-Total-Count": str(total)})


@router.get("/near-misses", response_model=list[MatchListItem])
async def get_near_misses(
    min_score: int = Query(default=30, ge=0, le=100),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    from sqlmodel import func

    total = session.exec(
        select(func.count()).select_from(Match)
        .where(Match.status == "low_match")
        .where(Match.score >= min_score)
    ).one()
    matches = session.exec(
        select(Match, Job, Company)
        .join(Job, Match.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(Match.status == "low_match")
        .where(Match.score >= min_score)
        .order_by(Match.score.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    from fastapi.responses import JSONResponse
    items = [
        MatchListItem(
            id=m.id, score=m.score, reasoning=m.reasoning, status=m.status,
            matched_at=m.matched_at, job_title=j.title, company_name=c.name,
        ).model_dump(mode="json")
        for m, j, c in matches
    ]
    return JSONResponse(content=items, headers={"X-Total-Count": str(total)})


@router.get("/{match_id}", response_model=MatchDetail)
async def get_match_detail(match_id: int, session: Session = Depends(get_session)):
    result = session.exec(
        select(Match, Job, Company)
        .join(Job, Match.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(Match.id == match_id)
    ).first()

    if not result:
        raise HTTPException(status_code=404, detail="Match not found")

    match, job, company = result

    cv_variant = None
    ambiguous_variants = []
    if match.cv_variant_id:
        cv = session.get(CVVariant, match.cv_variant_id)
        if cv:
            cv_variant = CVVariantOut(id=cv.id, name=cv.name, file_path=cv.file_path, focus_tags=cv.focus_tags)
    else:
        # Check for ambiguous variants using the job description keywords
        from app.pipeline.cv_selector import select_cv_variant
        active = list(session.exec(select(CVVariant).where(CVVariant.is_active == True)).all())
        if len(active) >= 2:
            selected = select_cv_variant(job.title, active)
            if len(selected) >= 2:
                ambiguous_variants = [
                    CVVariantOut(id=v.id, name=v.name, file_path=v.file_path, focus_tags=v.focus_tags)
                    for v in selected
                ]

    breakdown = None
    if match.score_breakdown:
        import json as _json
        try:
            bd = _json.loads(match.score_breakdown)
            breakdown = ScoreBreakdown(**bd)
        except Exception:
            pass

    ats_url = build_ats_apply_url(job.url, company.ats_type)

    return MatchDetail(
        id=match.id, score=match.score, reasoning=match.reasoning,
        status=match.status, matched_at=match.matched_at, reviewed_at=match.reviewed_at,
        score_breakdown=breakdown,
        job=JobOut(
            id=job.id, title=job.title, url=job.url,
            description_raw=job.description_raw, location=job.location, remote=job.remote,
        ),
        company=CompanyOut(id=company.id, name=company.name, website=company.website),
        cv_variant=cv_variant,
        ambiguous_variants=ambiguous_variants,
        ats_url=ats_url,
    )


@router.post("/{match_id}/skip")
async def skip_match(match_id: int, session: Session = Depends(get_session)):
    match = session.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.status = "skipped"
    match.reviewed_at = datetime.now(timezone.utc)
    session.add(match)
    session.commit()
    session.refresh(match)
    return {"id": match.id, "status": match.status}


@router.post("/{match_id}/promote")
async def promote_near_miss(match_id: int, session: Session = Depends(get_session)):
    match = session.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if match.status != "low_match":
        raise HTTPException(status_code=400, detail="Only low_match entries can be promoted")

    match.status = "new"
    match.reviewed_at = datetime.now(timezone.utc)
    session.add(match)
    session.commit()
    session.refresh(match)
    return {"id": match.id, "status": match.status}


@router.post("/{match_id}/applied")
async def apply_match(
    match_id: int,
    body: ApplyRequest,
    session: Session = Depends(get_session),
):
    match = session.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    job = session.get(Job, match.job_id)
    company = session.get(Company, job.company_id) if job else None

    if body.ats_url:
        ats_url = body.ats_url
    elif job and company:
        ats_url = build_ats_apply_url(job.url, company.ats_type)
    else:
        ats_url = ""

    cv_variant_id = body.chosen_cv_variant_id or match.cv_variant_id

    match.status = "applied"
    match.reviewed_at = datetime.now(timezone.utc)
    session.add(match)

    application = Application(
        match_id=match.id,
        cv_variant_id=cv_variant_id,
        ats_url=ats_url,
        outcome_status="pending",
    )
    session.add(application)
    session.commit()
    session.refresh(match)
    session.refresh(application)

    return {
        "match": MatchListItem(
            id=match.id, score=match.score, reasoning=match.reasoning,
            status=match.status, matched_at=match.matched_at,
            job_title=job.title if job else "", company_name=company.name if company else "",
        ),
        "application": {
            "id": application.id,
            "outcome_status": application.outcome_status,
            "applied_at": application.applied_at.isoformat(),
        },
        "ats_url": ats_url,
    }
