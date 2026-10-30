from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine
from app.importers.scheduler import start_scheduler, stop_scheduler
from app.routers import (
    admin,
    applications,
    auth,
    jobs,
    profile,
    profile_items,
    recruiter,
    resumes,
    swipes,
    autofill,
    explore,
    explore_web,
    autofill_ai,
    chat,
    trust,
    verification,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="SwipeX API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(verification.admin_router)
app.include_router(profile.router)
app.include_router(profile_items.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(swipes.router)
app.include_router(applications.router)
app.include_router(recruiter.router)
app.include_router(verification.recruiter_router)
app.include_router(trust.router)
app.include_router(autofill.router)
app.include_router(explore.router)
app.include_router(explore_web.router)
app.include_router(autofill_ai.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "swipex-api"}


@app.get("/health/db")
def health_db():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "ok"}