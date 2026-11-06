import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.models import SystemStatus

WORKER_FRESH_SECONDS = 180


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def set_status(key, value):
    now = now_utc()
    with SessionLocal() as db:
        statement = insert(SystemStatus).values(key=key, value=value, updated_at=now)
        db.execute(
            statement.on_conflict_do_update(index_elements=["key"], set_={"value": value, "updated_at": now})
        )
        db.commit()


def get_status(key):
    """Returns (value, updated_at) or None."""
    with SessionLocal() as db:
        row = db.scalar(select(SystemStatus).where(SystemStatus.key == key))
        return (row.value, row.updated_at) if row else None


def age_seconds(moment):
    return max(0, int((now_utc() - moment).total_seconds()))


def heartbeat():
    set_status("worker_heartbeat", "alive")


def record_import(totals):
    set_status("last_import", json.dumps(totals if totals is not None else {}, default=str)[:1000])