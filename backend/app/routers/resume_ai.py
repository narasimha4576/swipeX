from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Company, Job, Resume, User
from app.resume_tools import analyze_resume, match_job, page_count, read_pdf
from app.routers.resumes import UPLOAD_DIR

router = APIRouter(tags=["resume-ai"])
seeker_only = require_roles("job_seeker")


class ResumeAnalysisOut(BaseModel):
    resume_id: int
    name: str
    pages: int
    words: int
    readable: bool
    score: int
    skills: list[str]
    sections: dict[str, bool]
    contact: dict[str, bool]
    tips: list[str]


class MatchOut(BaseModel):
    resume_id: int
    resume_name: str
    score: int
    label: str
    matched_skills: list[str]
    missing_skills: list[str]
    text_match_percent: int
    tips: list[str]


def load_text(db: Session, user: User, resume_id: int):
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    path = UPLOAD_DIR / resume.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="The resume file is missing")
    text = resume.parsed_text or ""
    if not text:
        text, _ = read_pdf(path)
        if text:
            resume.parsed_text = text
            db.commit()
    return resume, text, page_count(path)


@router.get("/resumes/{resume_id}/analysis", response_model=ResumeAnalysisOut)
def resume_analysis(
    resume_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    resume, text, pages = load_text(db, user, resume_id)
    return ResumeAnalysisOut(resume_id=resume.id, name=resume.version_name, **analyze_resume(text, pages))


@router.get("/jobs/{job_id}/match", response_model=MatchOut)
def job_match(
    job_id: int,
    resume_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    row = db.execute(
        select(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .where(Job.id == job_id, Company.verification_status != "rejected")
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job = row[0]

    if resume_id is None:
        default = db.scalar(
            select(Resume)
            .where(Resume.user_id == user.id)
            .order_by(Resume.is_default.desc(), Resume.id.desc())
        )
        if default is None:
            raise HTTPException(status_code=400, detail="Upload a resume first")
        resume_id = default.id

    resume, text, _ = load_text(db, user, resume_id)
    result = match_job(text, job.skills or [], job.title, job.description)
    return MatchOut(resume_id=resume.id, resume_name=resume.version_name, **result)

from app.ai import AIUnavailable
from app.resume_tailor import tailor


class Rewrite(BaseModel):
    before: str
    after: str


class TipsOut(BaseModel):
    summary: str | None = None
    rewrites: list[Rewrite]
    removed: int = 0


@router.post("/jobs/{job_id}/resume-tips", response_model=TipsOut)
def resume_tips(
    job_id: int,
    resume_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    row = db.execute(
        select(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .where(Job.id == job_id, Company.verification_status != "rejected")
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job, company = row

    if resume_id is None:
        default = db.scalar(
            select(Resume)
            .where(Resume.user_id == user.id)
            .order_by(Resume.is_default.desc(), Resume.id.desc())
        )
        if default is None:
            raise HTTPException(status_code=400, detail="Upload a resume first")
        resume_id = default.id

    resume, text, _ = load_text(db, user, resume_id)
    if len(text.strip()) < 200:
        raise HTTPException(
            status_code=400,
            detail="Your resume text could not be read. Use a text PDF, not a scan.",
        )
    try:
        result = tailor(
            f"{user.id}:{resume.id}:{job.id}",
            user.id,
            text,
            job.title,
            company.name,
            job.description,
            job.skills or [],
        )
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except AIUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return TipsOut(**result)