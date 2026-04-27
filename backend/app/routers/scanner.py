from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel import Session

from app.database import get_session
from app.scheduler import run_full_scan, scan_state, scheduler

router = APIRouter()


@router.post("/trigger-scan")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    if scan_state["is_running"]:
        return {"message": "Scan already in progress"}

    background_tasks.add_task(run_full_scan, session)
    return {"message": "Scan triggered"}


@router.get("/scan-status")
async def get_scan_status():
    job = scheduler.get_job("job_scan")
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {**scan_state, "next_scan_at": next_run}
