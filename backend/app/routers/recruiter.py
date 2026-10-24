from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Company, Job, RecruiterProfile, User
from app.routers.jobs import job_to_out
from app.schemas import CompanyOut, CompanyUpdate, JobCreate, MyJobOut

router = APIRouter(prefix="/recruiter", tags=["recruiter"])
recruiter_only = require_roles("recruiter")


def get_my_company(db: Session, user: User) -> Company | None:
    return db.scalar(
        select(Company)
        .join(RecruiterProfile, RecruiterProfile.company_id == Company.id)
        .where(RecruiterProfile.user_id == user.id)
    )


def to_my_job_out(job: Job, company: Company) -> MyJobOut:
    base = job_to_out(job, company)
    return MyJobOut(**base.model_dump(), is_active=job.is_active)


@router.get("/company", response_model=CompanyOut | None)
def read_company(
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_only),
):
    return get_my_company(db, user)


@router.put("/company", response_model=CompanyOut)
def save_company(
    data: CompanyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_only),
):
    name = data.name.strip()
    company = get_my_company(db, user)

    clash = db.scalar(select(Company).where(func.lower(Company.name) == name.lower()))
    if clash is not None and (company is None or clash.id != company.id):
        raise HTTPException(status_code=400, detail="A company with this name already exists")

    location = (data.location or "").strip() or None
    if company is None:
        company = Company(
            name=name,
            company_type=data.company_type,
            location=location,
            website=data.website,
            founded_year=data.founded_year,
        )
        db.add(company)
        db.flush()
        db.add(RecruiterProfile(user_id=user.id, company_id=company.id))
    else:
        company.name = name
        company.company_type = data.company_type
        company.location = location
        company.website = data.website
        company.founded_year = data.founded_year

    db.commit()
    db.refresh(company)
    return company


@router.get("/jobs", response_model=list[MyJobOut])
def my_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_only),
):
    rows = db.execute(
        select(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .where(Job.posted_by == user.id)
        .order_by(Job.created_at.desc(), Job.id.desc())
    ).all()
    return [to_my_job_out(job, company) for job, company in rows]


@router.post("/jobs", response_model=MyJobOut, status_code=status.HTTP_201_CREATED)
def post_job(
    data: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_only),
):
    company = get_my_company(db, user)
    if company is None:
        raise HTTPException(status_code=400, detail="Create your company profile first")

    location = (data.location or "").strip() or ("Remote" if data.is_remote else None)
    job = Job(
        company_id=company.id,
        posted_by=user.id,
        title=data.title.strip(),
        description=data.description.strip(),
        location=location,
        is_remote=data.is_remote,
        job_type=data.job_type,
        experience_level=data.experience_level,
        salary_min_lpa=data.salary_min_lpa,
        salary_max_lpa=data.salary_max_lpa,
        skills=data.skills,
        applicant_count=0,
        is_active=True,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return to_my_job_out(job, company)


@router.patch("/jobs/{job_id}/active", response_model=MyJobOut)
def set_job_active(
    job_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_only),
):
    job = db.get(Job, job_id)
    if job is None or job.posted_by != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_active = is_active
    db.commit()
    db.refresh(job)
    company = db.get(Company, job.company_id)
    return to_my_job_out(job, company)