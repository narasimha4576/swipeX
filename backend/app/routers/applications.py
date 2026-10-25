from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Application, Company, Job, Resume, Swipe, User
from app.routers.jobs import job_to_out
from app.schemas import ApplicationOut, ApplyIn

router = APIRouter(prefix="/applications", tags=["applications"])
seeker_only = require_roles("job_seeker")


def to_out(
    application: Application, job: Job, company: Company, resume_name: str | None
) -> ApplicationOut:
    return ApplicationOut(
        id=application.id,
        status=application.status,
        created_at=application.created_at,
        updated_at=application.updated_at,
        resume_name=resume_name,
        job=job_to_out(job, company),
    )


@router.get("", response_model=list[ApplicationOut])
def my_applications(
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    names = {
        r.id: r.version_name
        for r in db.scalars(select(Resume).where(Resume.user_id == user.id))
    }
    rows = db.execute(
        select(Application, Job, Company)
        .join(Job, Application.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(Application.user_id == user.id)
        .order_by(Application.updated_at.desc(), Application.id.desc())
    ).all()
    return [
        to_out(application, job, company, names.get(application.resume_id))
        for application, job, company in rows
    ]


@router.post("/apply", response_model=ApplicationOut)
def apply(
    data: ApplyIn,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    job = db.get(Job, data.job_id)
    if job is None or not job.is_active:
        raise HTTPException(status_code=404, detail="This job is not open any more")

    resume = db.get(Resume, data.resume_id)
    if resume is None or resume.user_id != user.id:
        raise HTTPException(status_code=400, detail="Choose one of your own resumes")

    application = db.scalar(
        select(Application).where(
            Application.user_id == user.id, Application.job_id == job.id
        )
    )
    if application is not None and application.status != "saved":
        raise HTTPException(status_code=400, detail="You already applied to this job")

    if application is None:
        application = Application(
            user_id=user.id, job_id=job.id, resume_id=resume.id, status="applied"
        )
        db.add(application)
    else:
        application.resume_id = resume.id
        application.status = "applied"

    swipe = db.scalar(
        select(Swipe).where(Swipe.user_id == user.id, Swipe.job_id == job.id)
    )
    if swipe is None:
        db.add(Swipe(user_id=user.id, job_id=job.id, direction="right"))
    elif swipe.direction != "right":
        swipe.direction = "right"

    db.execute(
        update(Job).where(Job.id == job.id).values(applicant_count=Job.applicant_count + 1)
    )
    db.commit()
    db.refresh(application)
    db.refresh(job)

    company = db.get(Company, job.company_id)
    return to_out(application, job, company, resume.version_name)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_saved(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    application = db.get(Application, application_id)
    if application is None or application.user_id != user.id:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.status != "saved":
        raise HTTPException(status_code=400, detail="Only saved jobs can be removed")

    swipe = db.scalar(
        select(Swipe).where(
            Swipe.user_id == user.id, Swipe.job_id == application.job_id
        )
    )
    if swipe is not None:
        swipe.direction = "left"

    db.delete(application)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)