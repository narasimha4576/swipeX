import hashlib
import logging
import re
import traceback
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.responses import JSONResponse
from sqlalchemy import delete
from sqlalchemy.exc import DBAPIError
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.requests import ClientDisconnect

from app.database import SessionLocal
from app.models import ErrorEvent
from app.ratelimit import RateLimiter

log = logging.getLogger("swipex.errors")

store_limit = RateLimiter(20, 60, "")  # the same crash is stored at most 20 times a minute
client_error_limit = RateLimiter(10, 60, "Too many error reports. Please wait a minute.")

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
TOKEN = re.compile(r"eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}|(?i:bearer\s+\S+)")
LONG_NUMBER = re.compile(r"\d{7,}")
HEX_SEGMENT = re.compile(r"/[\w-]*[0-9a-f]{8,}[\w.-]*")


def scrub(text):
    """Hides emails, login tokens and long numbers."""
    text = EMAIL.sub("[email]", text or "")
    text = TOKEN.sub("[token]", text)
    return LONG_NUMBER.sub("[number]", text)


def clean_path(path):
    path = (path or "/").split("?")[0][:200]
    path = re.sub(r"/\d+", "/{id}", path)
    return HEX_SEGMENT.sub("/{token}", path)


def describe(exc):
    """The error type and only the first line of its message (database errors put people's data on line 2)."""
    base = exc.orig if isinstance(exc, DBAPIError) and getattr(exc, "orig", None) is not None else exc
    first = (str(base).splitlines() or [""])[0]
    return type(base).__name__, scrub(first)[:300]


def short_trace(exc):
    lines = []
    for frame in traceback.extract_tb(exc.__traceback__)[-12:]:
        name = re.sub(r".*[\\/](backend|site-packages)[\\/]", r"\1/", frame.filename)
        lines.append(f"{name}:{frame.lineno} in {frame.name}")
        if frame.line:
            lines.append(f"    {frame.line}")
    return scrub("\n".join(lines))


def store_event(*, kind, message, trace, method, path, source, status_code=500, fingerprint=None):
    """Saves one error report and returns its reference code. Never raises."""
    error_id = uuid4().hex[:8].upper()
    fingerprint = fingerprint or hashlib.sha1(f"{kind}|{path}|{message[:60]}".encode()).hexdigest()[:12]
    try:
        if store_limit.retry_after(fingerprint):
            return error_id
        store_limit.add(fingerprint)
        with SessionLocal() as db:
            db.add(
                ErrorEvent(
                    error_id=error_id,
                    fingerprint=fingerprint,
                    kind=kind[:120],
                    message=message[:300],
                    trace=trace[:6000],
                    method=method[:10],
                    path=path[:200],
                    status_code=status_code,
                    source=source,
                )
            )
            db.commit()
    except Exception:
        log.exception("Could not store an error report")
    return error_id


def record_exception(exc, *, method, path, source="api"):
    kind, message = describe(exc)
    frames = traceback.extract_tb(exc.__traceback__)
    where = f"{frames[-1].filename}:{frames[-1].name}" if frames else ""
    fingerprint = hashlib.sha1(f"{kind}|{path}|{where}".encode()).hexdigest()[:12]
    return store_event(
        kind=kind,
        message=message,
        trace=short_trace(exc) + f"\n{kind}: {message}",
        method=method,
        path=path,
        source=source,
        fingerprint=fingerprint,
    )


class CaptureErrors:
    """Catches crashes that nothing else handled, saves them, and answers with a clean 500."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = False

        async def watch(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, watch)
        except ClientDisconnect:
            raise
        except Exception as exc:
            method = scope.get("method", "GET")
            path = clean_path(scope.get("path", "/"))
            error_id = await run_in_threadpool(record_exception, exc, method=method, path=path)
            log.error("Unhandled error %s on %s %s", error_id, method, path, exc_info=exc)
            if started:
                raise
            reply = JSONResponse(
                {
                    "detail": f"Something went wrong on our side (reference {error_id}). Please try again.",
                    "error_id": error_id,
                },
                status_code=500,
            )
            await reply(scope, receive, send)


def install_error_tracking(app):
    # Added last, so it sits closest to the routes and the CORS headers still reach the browser.
    app.user_middleware.append(Middleware(CaptureErrors))


def report_job_error(event):
    """Called by the scheduler when a background job fails."""
    if event.exception is not None:
        record_exception(event.exception, method="JOB", path=f"worker:{event.job_id}", source="worker")


def cleanup_old_errors(days=30):
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    with SessionLocal() as db:
        result = db.execute(delete(ErrorEvent).where(ErrorEvent.created_at < cutoff))
        db.commit()
    return result.rowcount or 0