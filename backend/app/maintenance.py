import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.database import SessionLocal
from app.models import Swipe

SKIP_RETENTION_DAYS = int(os.getenv("SKIP_RETENTION_DAYS", "15"))


def cleanup_old_skips() -> int:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=SKIP_RETENTION_DAYS)
    with SessionLocal() as db:
        result = db.execute(
            delete(Swipe).where(Swipe.direction == "left", Swipe.updated_at < cutoff)
        )
        db.commit()
    removed = result.rowcount or 0
    if removed:
        print(
            f"Cleanup: removed {removed} skipped jobs older than {SKIP_RETENTION_DAYS} days",
            flush=True,
        )
    return removed