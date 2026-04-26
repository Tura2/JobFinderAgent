from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.database import create_db_and_tables
from app.middleware.session import SessionMiddleware
from app.routers import matches, companies, tracker, cv_variants, scanner
from app.routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    try:
        from app.scheduler import start_scheduler
        start_scheduler()
    except Exception:
        pass
    yield


app = FastAPI(
    title="JobFinderAgent",
    description="Autonomous Job Hunting Pipeline API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.pwa_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["auth"])
app.include_router(matches.router, prefix="/matches", tags=["matches"])
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(tracker.router, tags=["tracker"])
app.include_router(cv_variants.router, prefix="/cv-variants", tags=["cv-variants"])
app.include_router(scanner.router, tags=["scanner"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "jobfinder-agent"}


pwa_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if pwa_dist.exists():
    app.mount("/", StaticFiles(directory=str(pwa_dist), html=True), name="pwa")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
