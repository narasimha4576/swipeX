import json
import platform
import shutil
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.admin_audit import log_admin
from app.ai import is_configured as ai_configured
from app.deps import get_db, require_roles
from app.models import ErrorEvent, User
from app.routers import resumes
from app.security_setup import is_production
from app.status import WORKER_FRESH_SECONDS, age_seconds, get_status

router = APIRouter(prefix="/admin", tags=["admin-system"])
admin_only = require_roles("admin")
STARTED = time.time()


def hours_ago(hours):
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)


@router.get("/system")
def system_status(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    started = time.perf_counter()
    db.execute(text("SELECT 1"))
    latency = round((time.perf_counter() - started) * 1000, 1)

    try:
        version = db.scalar(text("SELECT version_num FROM alembic_version"))
    except Exception:
        db.rollback()
        version = None

    heartbeat = get_status("worker_heartbeat")
    if heartbeat is None:
        worker = {"status": "unknown", "seconds": None}
    else:
        seconds = age_seconds(heartbeat[1])
        worker = {"status": "ok" if seconds <= WORKER_FRESH_SECONDS else "stale", "seconds": seconds}

    last_import = get_status("last_import")
    try:
        free_mb = shutil.disk_usage(resumes.UPLOAD_DIR).free // (1024 * 1024)
    except Exception:
        free_mb = None

    def errors_since(hours):
        return db.scalar(
            select(func.count()).select_from(ErrorEvent).where(ErrorEvent.created_at >= hours_ago(hours))
        )

    return jsonable_encoder(
        {
            "database": {"ok": True, "latency_ms": latency, "schema_version": version},
            "worker": worker,
            "last_import": (
                {"at": last_import[1], "summary": json.loads(last_import[0] or "{}")} if last_import else None
            ),
            "uploads": {"free_mb": free_mb},
            "ai_configured": bool(ai_configured()),
            "errors_24h": errors_since(24),
            "errors_7d": errors_since(24 * 7),
            "environment": "production" if is_production() else "development",
            "python": platform.python_version(),
            "uptime_minutes": int((time.time() - STARTED) // 60),
        }
    )


@router.get("/errors")
def list_errors(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    since = hours_ago(24 * days)
    groups = db.execute(
        select(
            ErrorEvent.fingerprint,
            func.count(),
            func.min(ErrorEvent.created_at),
            func.max(ErrorEvent.created_at),
        )
        .where(ErrorEvent.created_at >= since)
        .group_by(ErrorEvent.fingerprint)
        .order_by(func.max(ErrorEvent.created_at).desc())
        .limit(50)
    ).all()
    out = []
    for fingerprint, count, first_seen, last_seen in groups:
        latest = db.scalar(
            select(ErrorEvent).where(ErrorEvent.fingerprint == fingerprint).order_by(ErrorEvent.id.desc()).limit(1)
        )
        out.append(
            {
                "fingerprint": fingerprint,
                "count": count,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "kind": latest.kind,
                "message": latest.message,
                "method": latest.method,
                "path": latest.path,
                "source": latest.source,
                "error_id": latest.error_id,
            }
        )
    return jsonable_encoder(out)


@router.get("/errors/{fingerprint}")
def error_detail(
    fingerprint: str,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    events = db.scalars(
        select(ErrorEvent).where(ErrorEvent.fingerprint == fingerprint).order_by(ErrorEvent.id.desc()).limit(10)
    ).all()
    if not events:
        raise HTTPException(status_code=404, detail="Error not found")
    latest = events[0]
    return jsonable_encoder(
        {
            "fingerprint": fingerprint,
            "kind": latest.kind,
            "message": latest.message,
            "trace": latest.trace,
            "method": latest.method,
            "path": latest.path,
            "source": latest.source,
            "occurrences": [{"error_id": e.error_id, "at": e.created_at} for e in events],
        }
    )


@router.post("/errors/clear")
def clear_errors(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    result = db.execute(delete(ErrorEvent))
    log_admin(db, admin, "cleared_errors", None, f"{result.rowcount or 0} entries")
    db.commit()
    return {"removed": result.rowcount or 0}


if not is_production():

    @router.post("/test-error")
    def create_test_error(admin: User = Depends(admin_only)):
        """Development only: makes the website crash on purpose so you can see the error tracking work."""
        raise RuntimeError("Test error created by an admin. Nothing is actually wrong.")