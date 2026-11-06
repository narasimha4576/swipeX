import os
import shutil

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.database import engine
from app.errors import clean_path, client_error_limit, scrub, store_event
from app.ratelimit import client_ip
from app.routers import resumes
from app.status import WORKER_FRESH_SECONDS, age_seconds, get_status

router = APIRouter(tags=["monitoring"])


@router.get("/health/ready")
def ready(response: Response):
    """200 when the website can do its job. For uptime monitors and load balancers."""
    checks = {}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "down"
    try:
        folder = resumes.UPLOAD_DIR
        folder.mkdir(parents=True, exist_ok=True)
        if not os.access(folder, os.W_OK):
            checks["uploads"] = "not_writable"
        elif shutil.disk_usage(folder).free < 100 * 1024 * 1024:
            checks["uploads"] = "low_disk"
        else:
            checks["uploads"] = "ok"
    except Exception:
        checks["uploads"] = "problem"
    healthy = all(value == "ok" for value in checks.values())
    if not healthy:
        response.status_code = 503
    return {"status": "ok" if healthy else "degraded", "checks": checks}


@router.get("/health/worker")
def worker(response: Response):
    """200 when the background worker has said "still alive" in the last 3 minutes."""
    try:
        row = get_status("worker_heartbeat")
    except Exception:
        response.status_code = 503
        return {"status": "database_down"}
    if row is None:
        response.status_code = 503
        return {"status": "unknown"}
    seconds = age_seconds(row[1])
    if seconds > WORKER_FRESH_SECONDS:
        response.status_code = 503
        return {"status": "stale", "seconds_since_heartbeat": seconds}
    return {"status": "ok", "seconds_since_heartbeat": seconds}


class ClientError(BaseModel):
    message: str = Field(max_length=300)
    stack: str | None = Field(default=None, max_length=3000)
    page: str | None = Field(default=None, max_length=200)


@router.post("/errors/client", status_code=204)
def report_browser_error(data: ClientError, request: Request):
    """The website reports a page that crashed. No login needed, but it is limited and cleaned."""
    client_error_limit.hit(client_ip(request))
    store_event(
        kind="BrowserError",
        message=scrub(data.message)[:300],
        trace=scrub(data.stack or "")[:3000],
        method="PAGE",
        path=clean_path(data.page or "/"),
        source="browser",
        status_code=0,
    )
    return Response(status_code=204)