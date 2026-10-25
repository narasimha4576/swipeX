from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import (
    Application,
    Company,
    Experience,
    Job,
    PortfolioItem,
    Profile,
    RecruiterProfile,
    Resume,
    User,
)
from app.routers.jobs import job_to_out
from app.routers.resumes import UPLOAD_DIR
from app.schemas import (
    ApplicantOut,
    CompanyOut,
    CompanyUpdate,
    ExperienceOut,
    JobCreate,
    MyJobOut,
    PortfolioOut,
    StatusUpdate,
)

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
        if company.verification_status == "verified" and (
            company.name != name or company.website != data.website
        ):
            company.verification_status = "pending"
            company.verified_at = None
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


APPLICATION_STATUSES = ("applied", "shortlisted", "interview", "rejected")


def get_my_job(db: Session, user: User, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.posted_by != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def get_my_application(db: Session, user: User, application_id: int) -> Application:
    application = db.get(Application, application_id)
    if application is None or application.status == "saved":
        raise HTTPException(status_code=404, detail="Application not found")
    job = db.get(Job, application.job_id)
    if job is None or job.posted_by != user.id:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.get("/jobs/{job_id}/applicants", response_model=list[ApplicantOut])
def list_applicants(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_only),
):
    job = get_my_job(db, user, job_id)
    rows = db.execute(
        select(Application, User, Profile, Resume)
        .join(User, Application.user_id == User.id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .outerjoin(Resume, Application.resume_id == Resume.id)
        .where(
            Application.job_id == job.id,
            Application.status.in_(APPLICATION_STATUSES),
        )
        .order_by(Application.updated_at.desc(), Application.id.desc())
    ).all()

    result = []
    for application, candidate, profile, resume in rows:
        experiences = db.scalars(
            select(Experience)
            .where(Experience.user_id == candidate.id)
            .order_by(Experience.start_year.desc(), Experience.id.desc())
        ).all()
        portfolio = db.scalars(
            select(PortfolioItem)
            .where(PortfolioItem.user_id == candidate.id)
            .order_by(PortfolioItem.id.desc())
        ).all()
        result.append(
            ApplicantOut(
                application_id=application.id,
                status=application.status,
                updated_at=application.updated_at,
                full_name=candidate.full_name,
                email=candidate.email,
                headline=profile.headline if profile else None,
                location=profile.location if profile else None,
                experience_years=profile.experience_years if profile else 0,
                skills=(profile.skills or []) if profile else [],
                bio=profile.bio if profile else None,
                resume_name=resume.version_name if resume else None,
                experiences=[ExperienceOut.model_validate(e) for e in experiences],
                portfolio=[PortfolioOut.model_validate(p) for p in portfolio],
            )
        )
    return result


@router.patch("/applications/{application_id}/status", response_model=StatusUpdate)
def update_application_status(
    application_id: int,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_only),
):
    application = get_my_application(db, user, application_id)
    application.status = data.status
    db.commit()
    return StatusUpdate(status=application.status)


@router.get("/applications/{application_id}/resume")
def applicant_resume(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_only),
):
    application = get_my_application(db, user, application_id)
    resume = db.get(Resume, application.resume_id) if application.resume_id else None
    if resume is None:
        raise HTTPException(status_code=404, detail="No resume attached")
    path = UPLOAD_DIR / resume.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Resume file is missing")
    return FileResponse(
        path, media_type="application/pdf", filename=f"{resume.version_name}.pdf"
    )