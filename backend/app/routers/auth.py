import asyncio
from pathlib import Path

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config import settings
from app.middleware.session import make_session_cookie

router = APIRouter()

_LOGIN_HTML = (Path(__file__).parent.parent / "login.html").read_text()


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page():
    return HTMLResponse(_LOGIN_HTML)


@router.post("/auth/login")
async def login(password: str = Form(...)):
    if password != settings.pwa_access_token:
        await asyncio.sleep(1)
        return RedirectResponse("/login?error=1", status_code=302)
    cookie_val = make_session_cookie(settings.session_secret_key, settings.session_max_age_days)
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(
        key="session",
        value=cookie_val,
        max_age=settings.session_max_age_days * 86400,
        httponly=True,
        samesite="strict",
    )
    return resp


@router.post("/auth/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("session")
    return resp


@router.get("/config")
async def get_config():
    return JSONResponse({"linkedin_url": settings.applicant_linkedin_url})
