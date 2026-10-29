from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Company, Job, User
from app.schemas import CompanyOut, JobOut, JobPage, SafetyFlag, SafetyOut
from app.safety import analyze

router = APIRouter(tags=["jobs"])

LOW_COMPETITION_MAX = 60
HIGH_COMPETITION_MIN = 200


def competition_level(applicants: int) -> str:
    if applicants < LOW_COMPETITION_MAX:
        return "low"
    if applicants >= HIGH_COMPETITION_MIN:
        return "high"
    return "medium"


def job_to_out(job: Job, company: Company) -> JobOut:
    return JobOut(
        id=job.id,
        title=job.title,
        description=job.description,
        location=job.location,
        is_remote=job.is_remote,
        job_type=job.job_type,
        experience_level=job.experience_level,
        salary_min_lpa=job.salary_min_lpa,
        salary_max_lpa=job.salary_max_lpa,
        skills=job.skills or [],
        applicant_count=job.applicant_count,
        competition_level=(
            competition_level(job.applicant_count)
            if job.source == "native"
            else "unknown"
        ),
        source=job.source,
        apply_url=job.apply_url,
        created_at=job.created_at,
        company=CompanyOut.model_validate(company),
    )


@router.get("/jobs", response_model=JobPage)
def list_jobs(
    q: str | None = None,
    company_type: str | None = None,
    job_type: str | None = None,
    experience_level: str | None = None,
    remote: bool | None = None,
    location: str | None = None,
    skill: str | None = None,
    min_salary: float | None = Query(None, ge=0),
    max_age_days: int | None = Query(None, ge=1, le=365),
    verified_only: bool = True,
    fresher_friendly: bool = False,
    low_competition: bool = False,
    sort: Literal["newest", "salary", "competition"] = "newest",
    page: int = Query(1, ge=1),
    page_size: int = Query(9, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conditions = [Job.is_active.is_(True)]
    if verified_only:
        conditions.append(Company.verification_status == "verified")
    else:
        conditions.append(Company.verification_status != "rejected")

    if q and q.strip():
        pattern = f"%{q.strip()}%"
        conditions.append(
            or_(
                Job.title.ilike(pattern),
                Company.name.ilike(pattern),
                cast(Job.skills, Text).ilike(pattern),
            )
        )
    if company_type:
        conditions.append(Company.company_type == company_type)
    if job_type:
        conditions.append(Job.job_type == job_type)
    if experience_level:
        conditions.append(Job.experience_level == experience_level)
    if remote is not None:
        conditions.append(Job.is_remote.is_(remote))
    if location and location.strip():
        conditions.append(Job.location.ilike(f"%{location.strip()}%"))
    if skill and skill.strip():
        clean = skill.strip().replace('"', "")
        conditions.append(cast(Job.skills, Text).ilike(f'%"{clean}"%'))
    if min_salary is not None:
        conditions.append(Job.salary_max_lpa >= min_salary)
    if max_age_days is not None:
        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            days=max_age_days
        )
        conditions.append(Job.created_at >= since)
    if fresher_friendly:
        conditions.append(
            or_(Job.experience_level == "fresher", Job.job_type.in_(["internship", "apprenticeship"]))
        )
    if low_competition:
        conditions.append(Job.applicant_count < LOW_COMPETITION_MAX)
        conditions.append(Job.source == "native")

    if sort == "salary":
        order = [Job.salary_max_lpa.desc().nulls_last(), Job.id.desc()]
    elif sort == "competition":
        order = [Job.applicant_count.asc(), Job.id.desc()]
    else:
        order = [Job.created_at.desc(), Job.id.desc()]

    total = db.scalar(
        select(func.count())
        .select_from(Job)
        .join(Company, Job.company_id == Company.id)
        .where(*conditions)
    )
    stmt = (
        select(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .where(*conditions)
        .order_by(*order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(stmt).all()
    return JobPage(
        items=[job_to_out(job, company) for job, company in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .where(Job.id == job_id, Job.is_active.is_(True), Company.verification_status != "rejected")
    )
    row = db.execute(stmt).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_out(row[0], row[1])


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(
    company_type: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Company).where(Company.verification_status == "verified").order_by(Company.name)
    if company_type:
        stmt = stmt.where(Company.company_type == company_type)
    return db.scalars(stmt).all()


@router.get("/jobs/{job_id}/safety", response_model=SafetyOut)
def job_safety(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.execute(
        select(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .where(Job.id == job_id, Company.verification_status != "rejected")
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    result = analyze(row[0], row[1])
    return SafetyOut(
        level=result.level,
        flags=[SafetyFlag(severity=f.severity, text=f.text) for f in result.flags],
        good=result.good,
    )