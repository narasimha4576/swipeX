import base64
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Company, Job, Profile, Resume, User
from app.routers.profile import get_or_create_profile
from app.routers.resumes import UPLOAD_DIR
from app.schemas import (
    ApplicationDetailsIn,
    ApplicationDetailsOut,
    AutofillApplicant,
    AutofillJob,
    AutofillPayload,
    AutofillResume,
)

router = APIRouter(prefix="/autofill", tags=["autofill"])
seeker_only = require_roles("job_seeker")

DETAIL_FIELDS = tuple(ApplicationDetailsIn.model_fields.keys())


def missing_items(profile: Profile, has_resume: bool) -> list[str]:
    missing = []
    if not profile.phone:
        missing.append("phone number")
    if not has_resume:
        missing.append("a resume")
    return missing


def count_resumes(db: Session, user: User) -> int:
    return db.scalar(
        select(func.count()).select_from(Resume).where(Resume.user_id == user.id)
    )


def details_out(db: Session, user: User, profile: Profile) -> ApplicationDetailsOut:
    missing = missing_items(profile, count_resumes(db, user) > 0)
    values = {field: getattr(profile, field) for field in DETAIL_FIELDS}
    return ApplicationDetailsOut(**values, ready=not missing, missing=missing)


@router.get("/details", response_model=ApplicationDetailsOut)
def get_details(
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    profile = get_or_create_profile(db, user)
    return details_out(db, user, profile)


@router.put("/details", response_model=ApplicationDetailsOut)
def save_details(
    data: ApplicationDetailsIn,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    profile = get_or_create_profile(db, user)
    for field, value in data.model_dump().items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return details_out(db, user, profile)


def personalize(text: str | None, name: str, company: str, title: str) -> str | None:
    if not text:
        return None
    return (
        text.replace("{{name}}", name)
        .replace("{{company}}", company)
        .replace("{{job_title}}", title)
    )


@router.get("/payload/{job_id}", response_model=AutofillPayload)
def autofill_payload(
    job_id: int,
    resume_id: int | None = Query(None),
    include_resume: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    row = db.execute(
        select(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .where(
            Job.id == job_id,
            Job.is_active.is_(True),
            Company.verification_status != "rejected",
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job, company = row
    if job.source == "native" or not job.apply_url:
        raise HTTPException(
            status_code=400,
            detail="Autofill is only for jobs that are applied for on the company site",
        )

    profile = get_or_create_profile(db, user)

    if resume_id is not None:
        resume = db.get(Resume, resume_id)
        if resume is None or resume.user_id != user.id:
            raise HTTPException(status_code=400, detail="Choose one of your own resumes")
    else:
        resume = db.scalar(
            select(Resume)
            .where(Resume.user_id == user.id)
            .order_by(Resume.is_default.desc(), Resume.id.desc())
        )

    resume_out = None
    if resume is not None:
        data_base64 = None
        if include_resume:
            path = UPLOAD_DIR / resume.file_path
            if not path.exists():
                raise HTTPException(status_code=404, detail="Resume file is missing")
            data_base64 = base64.b64encode(path.read_bytes()).decode("ascii")
        safe_name = re.sub(r"[^A-Za-z0-9._ -]", "", resume.version_name).strip() or "resume"
        resume_out = AutofillResume(
            id=resume.id,
            name=resume.version_name,
            filename=f"{safe_name}.pdf",
            data_base64=data_base64,
        )

    parts = user.full_name.split()
    first = parts[0] if parts else user.full_name
    last = " ".join(parts[1:]) or first

    applicant = AutofillApplicant(
        first_name=first,
        last_name=last,
        full_name=user.full_name,
        email=user.email,
        phone=profile.phone,
        location=profile.location,
        headline=profile.headline,
        linkedin_url=profile.linkedin_url,
        github_url=profile.github_url,
        portfolio_url=profile.portfolio_url,
        website=profile.portfolio_url or profile.github_url,
        college=profile.college,
        degree=profile.degree,
        discipline=profile.discipline,
        graduation_year=profile.graduation_year,
        authorized_countries=profile.authorized_countries,
        requires_sponsorship=profile.requires_sponsorship,
        willing_to_relocate=profile.willing_to_relocate,
        notice_period_days=profile.notice_period_days,
        current_ctc_lpa=profile.current_ctc_lpa,
        expected_ctc_lpa=profile.expected_ctc_lpa,
        cover_letter=personalize(profile.cover_letter, user.full_name, company.name, job.title),
        skills=profile.skills or [],
    )

    missing = missing_items(profile, resume is not None)
    return AutofillPayload(
        job=AutofillJob(
            id=job.id, title=job.title, company=company.name, apply_url=job.apply_url
        ),
        applicant=applicant,
        resume=resume_out,
        ready=not missing,
        missing=missing,
    )