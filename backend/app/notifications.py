from datetime import datetime, timezone

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Company, Job, Notification, SavedSearch
from app.search_filters import build_conditions

STATUS_TEXT = {"shortlisted": "Shortlisted", "interview": "Interview", "rejected": "Rejected"}


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def notify_status_change(db, application):
    label = STATUS_TEXT.get(application.status)
    if label is None:
        return
    job = db.get(Job, application.job_id)
    company = db.get(Company, job.company_id) if job else None
    if job is None or company is None:
        return
    db.add(
        Notification(
            user_id=application.user_id,
            kind="application",
            title=f"{company.name}: {label}"[:200],
            body=f"Your application for {job.title} was updated to {label}."[:500],
            link="/applications",
        )
    )
    db.commit()


def check_saved_searches():
    """Called after every job import. Creates one notification per search that has new jobs."""
    alerts = 0
    with SessionLocal() as db:
        latest = db.scalar(select(func.max(Job.id))) or 0
        for search in db.scalars(select(SavedSearch)):
            if latest <= search.last_job_id:
                continue
            conditions = build_conditions(search.filters or {})
            conditions += [Job.id > search.last_job_id, Job.id <= latest]
            count = (
                db.scalar(
                    select(func.count())
                    .select_from(Job)
                    .join(Company, Job.company_id == Company.id)
                    .where(*conditions)
                )
                or 0
            )
            search.last_job_id = latest
            if not count:
                continue
            existing = db.scalar(
                select(Notification).where(
                    Notification.user_id == search.user_id,
                    Notification.search_id == search.id,
                    Notification.is_read.is_(False),
                )
            )
            if existing:
                existing.count += count
                existing.title = f"{existing.count} new jobs for {search.name}"[:200]
                existing.created_at = now_utc()
            else:
                db.add(
                    Notification(
                        user_id=search.user_id,
                        kind="saved_search",
                        title=f"{count} new job{'s' if count != 1 else ''} for {search.name}"[:200],
                        body="Tap to see them.",
                        link=f"/jobs?search={search.id}",
                        search_id=search.id,
                        count=count,
                    )
                )
            alerts += 1
        db.commit()
    return alerts