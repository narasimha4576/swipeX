from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Application, Company, Job, Swipe, User
from app.routers.jobs import job_to_out
from app.schemas import DeckOut, SwipeCreate, SwipeOut

router = APIRouter(prefix="/swipes", tags=["swipes"])


@router.get("/deck", response_model=DeckOut)
def get_deck(
    limit: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("job_seeker")),
):
    already_swiped = select(Swipe.job_id).where(Swipe.user_id == user.id)
    conditions = [
        Job.is_active.is_(True),
        Company.verification_status == "verified",
        Job.id.not_in(already_swiped),
    ]

    rows = db.execute(
        select(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .where(*conditions)
        .order_by(Job.created_at.desc(), Job.id.desc())
        .limit(limit)
    ).all()

    remaining = db.scalar(
        select(func.count())
        .select_from(Job)
        .join(Company, Job.company_id == Company.id)
        .where(*conditions)
    )
    saved = db.scalar(
        select(func.count())
        .select_from(Swipe)
        .where(Swipe.user_id == user.id, Swipe.direction == "right")
    )
    skipped = db.scalar(
        select(func.count())
        .select_from(Swipe)
        .where(Swipe.user_id == user.id, Swipe.direction == "left")
    )
    return DeckOut(
        items=[job_to_out(job, company) for job, company in rows],
        remaining=remaining,
        saved=saved,
        skipped=skipped,
    )


@router.post("", response_model=SwipeOut)
def swipe(
    data: SwipeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("job_seeker")),
):
    job = db.get(Job, data.job_id)
    if job is None or not job.is_active:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = db.scalar(
        select(Swipe).where(Swipe.user_id == user.id, Swipe.job_id == data.job_id)
    )
    if existing:
        existing.direction = data.direction
    else:
        db.add(Swipe(user_id=user.id, job_id=data.job_id, direction=data.direction))

    if data.direction == "right":
        application = db.scalar(
            select(Application).where(
                Application.user_id == user.id, Application.job_id == data.job_id
            )
        )
        if application is None:
            db.add(Application(user_id=user.id, job_id=data.job_id, status="saved"))

    db.commit()
    return SwipeOut(job_id=data.job_id, direction=data.direction)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def undo_swipe(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("job_seeker")),
):
    existing = db.scalar(
        select(Swipe).where(Swipe.user_id == user.id, Swipe.job_id == job_id)
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Swipe not found")

    application = db.scalar(
        select(Application).where(
            Application.user_id == user.id, Application.job_id == job_id
        )
    )
    if application is not None and application.status == "saved":
        db.delete(application)

    db.delete(existing)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)