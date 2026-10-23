from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Company, Job, User
from app.schemas import CompanyOut, JobOut, JobPage

router = APIRouter(tags=["jobs"])


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
        created_at=job.created_at,
        company=CompanyOut.model_validate(company),
    )


@router.get("/jobs", response_model=JobPage)
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(9, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total = db.scalar(
        select(func.count()).select_from(Job).where(Job.is_active.is_(True))
    )
    stmt = (
        select(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .where(Job.is_active.is_(True))
        .order_by(Job.created_at.desc(), Job.id.desc())
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
        .where(Job.id == job_id, Job.is_active.is_(True))
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
    stmt = select(Company).order_by(Company.name)
    if company_type:
        stmt = stmt.where(Company.company_type == company_type)
    return db.scalars(stmt).all()