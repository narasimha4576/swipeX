from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import models  # noqa: F401  (this loads the tables)
from app.database import Base, engine
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
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SwipeX API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(profile.router)
app.include_router(profile_items.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(swipes.router)
app.include_router(applications.router)
app.include_router(recruiter.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "swipex-api"}


@app.get("/health/db")
def health_db():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "ok"}