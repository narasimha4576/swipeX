import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, exists, func

from app.database import SessionLocal
from app.models import Application, Job, Swipe


def cleanup_old_jobs(days=None):
    """Deletes imported jobs that closed long ago. Jobs people applied to or liked are always kept."""
    days = days or int(os.getenv("JOB_RETENTION_DAYS", "60"))
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    last_seen = func.coalesce(Job.last_seen_at, Job.created_at)
    statement = delete(Job).where(
        Job.source != "native",
        Job.is_active.is_(False),
        last_seen < cutoff,
        ~exists().where(Application.job_id == Job.id),
        ~exists().where(Swipe.job_id == Job.id),
    )
    with SessionLocal() as db:
        result = db.execute(statement)
        db.commit()
    return result.rowcount or 0