from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.exc import IntegrityError
from starlette.middleware import Middleware

import app.routers.monitoring as monitoring
from app.errors import (
    CaptureErrors,
    cleanup_old_errors,
    clean_path,
    describe,
    scrub,
    store_event,
)
from app.models import ErrorEvent, SystemStatus
from app.status import get_status, heartbeat, record_import, set_status


def crashing_client():
    small = FastAPI()
    small.user_middleware.append(Middleware(CaptureErrors))

    @small.get("/items/{item_id}")
    def boom(item_id: int):
        raise ValueError("boom for secret@example.com with eyJabcdefghij.abcdefghij.abcdefghij")

    return TestClient(small)


def events(db):
    db.expire_all()
    return db.scalars(select(ErrorEvent).order_by(ErrorEvent.id)).all()


# ---------- health checks ----------


def test_ready_is_ok_when_everything_works(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "uploads": "ok"}}


def test_ready_reports_trouble_when_the_database_is_down(client, monkeypatch):
    broken = create_engine("postgresql+psycopg://nobody:nopass@127.0.0.1:9/none", connect_args={"connect_timeout": 1})
    monkeypatch.setattr(monitoring, "engine", broken)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "down"


def test_worker_is_unknown_until_it_sends_a_sign_of_life(client):
    response = client.get("/health/worker")
    assert response.status_code == 503
    assert response.json()["status"] == "unknown"


def test_worker_is_ok_after_a_heartbeat(client):
    heartbeat()
    response = client.get("/health/worker")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_worker_is_stale_after_ten_minutes(client, db):
    heartbeat()
    old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)
    db.execute(update(SystemStatus).where(SystemStatus.key == "worker_heartbeat").values(updated_at=old))
    db.commit()
    response = client.get("/health/worker")
    assert response.status_code == 503
    assert response.json()["status"] == "stale"


# ---------- catching crashes ----------


def test_a_crash_is_answered_cleanly_and_saved(db):
    response = crashing_client().get("/items/5")
    assert response.status_code == 500
    body = response.json()
    assert "reference" in body["detail"]
    saved = events(db)
    assert len(saved) == 1
    assert saved[0].error_id == body["error_id"]
    assert saved[0].kind == "ValueError"
    assert saved[0].source == "api"


def test_saved_crashes_hide_personal_details_and_ids(db):
    crashing_client().get("/items/12345")
    saved = events(db)[0]
    assert "secret@example.com" not in saved.message and "[email]" in saved.message
    assert "eyJabcdefghij" not in saved.message and "[token]" in saved.message
    assert saved.path == "/items/{id}"
    assert "boom" in saved.trace  # the code line is kept, so you can find the bug


def test_the_same_crash_is_grouped(db):
    client = crashing_client()
    client.get("/items/1")
    client.get("/items/2")
    saved = events(db)
    assert len(saved) == 2
    assert saved[0].fingerprint == saved[1].fingerprint


def test_a_flood_of_the_same_crash_is_limited(db):
    client = crashing_client()
    for i in range(25):
        client.get(f"/items/{i}")
    assert len(events(db)) == 20


def test_normal_errors_are_not_counted_as_crashes(client, seeker, db):
    assert client.get("/jobs/99999", headers=seeker["headers"]).status_code == 404
    assert client.get("/auth/me").status_code == 401
    assert events(db) == []


def test_database_errors_keep_only_the_first_line():
    original = Exception("duplicate key value\nDETAIL: Key (email)=(a@b.com) already exists.")
    kind, message = describe(IntegrityError("INSERT ...", {"email": "a@b.com"}, original))
    assert message == "duplicate key value"
    assert "a@b.com" not in message


def test_scrub_and_clean_path():
    assert scrub("mail me at x@y.com or 12345678901") == "mail me at [email] or [number]"
    assert clean_path("/jobs/42/applicants?x=1") == "/jobs/{id}/applicants"
    assert clean_path("/public/profiles/narasimha-3f9a1c2b") == "/public/profiles/{token}"


def test_the_real_website_catches_crashes_too(client, admin, db):
    response = client.post("/admin/test-error", headers=admin["headers"])
    assert response.status_code == 500
    saved = events(db)
    assert saved[0].kind == "RuntimeError"
    assert saved[0].path == "/admin/test-error"
    assert saved[0].error_id == response.json()["error_id"]


# ---------- crashes reported by the browser ----------


def test_browser_crash_is_saved_and_cleaned(client, db):
    response = client.post(
        "/errors/client",
        json={"message": "x is undefined for me@example.com", "stack": "at Jobs (Jobs.jsx:10)", "page": "/jobs/42"},
    )
    assert response.status_code == 204
    saved = events(db)[0]
    assert saved.source == "browser"
    assert "me@example.com" not in saved.message
    assert saved.path == "/jobs/{id}"


def test_browser_reports_are_size_and_rate_limited(client):
    assert client.post("/errors/client", json={"message": "x" * 301}).status_code == 422
    for _ in range(10):
        assert client.post("/errors/client", json={"message": "oops"}).status_code == 204
    assert client.post("/errors/client", json={"message": "oops"}).status_code == 429


# ---------- the admin pages ----------


def test_admin_sees_grouped_errors_with_details(client, admin):
    for _ in range(3):
        store_event(
            kind="ValueError",
            message="boom",
            trace="Traceback text",
            method="GET",
            path="/items/{id}",
            source="api",
            fingerprint="abc123abc123",
        )
    groups = client.get("/admin/errors", headers=admin["headers"]).json()
    assert len(groups) == 1 and groups[0]["count"] == 3 and groups[0]["kind"] == "ValueError"
    detail = client.get("/admin/errors/abc123abc123", headers=admin["headers"]).json()
    assert detail["trace"] == "Traceback text"
    assert len(detail["occurrences"]) == 3
    assert client.get("/admin/errors/nothere", headers=admin["headers"]).status_code == 404


def test_admin_can_clear_errors_and_it_is_logged(client, admin):
    store_event(kind="E", message="m", trace="t", method="GET", path="/x", source="api")
    assert client.post("/admin/errors/clear", headers=admin["headers"]).json() == {"removed": 1}
    assert client.get("/admin/errors", headers=admin["headers"]).json() == []
    log = client.get("/admin/overview", headers=admin["headers"]).json()["activity_log"]
    assert log[0]["action"] == "cleared_errors"


def test_admin_system_report(client, admin):
    heartbeat()
    record_import({"added": 5, "closed": 1})
    data = client.get("/admin/system", headers=admin["headers"]).json()
    assert data["database"]["ok"] is True
    assert data["worker"]["status"] == "ok"
    assert data["last_import"]["summary"] == {"added": 5, "closed": 1}
    assert data["errors_24h"] == 0
    assert isinstance(data["ai_configured"], bool)


def test_normal_users_cannot_open_the_system_pages(client, seeker):
    for method, url in (
        ("get", "/admin/system"),
        ("get", "/admin/errors"),
        ("post", "/admin/errors/clear"),
        ("post", "/admin/test-error"),
    ):
        assert getattr(client, method)(url, headers=seeker["headers"]).status_code == 403


# ---------- housekeeping ----------


def test_old_errors_are_cleaned_up_and_new_ones_stay(db):
    old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=40)
    for created in (old, None):
        row = ErrorEvent(
            error_id="AAAA1111", fingerprint="f", kind="E", message="m", trace="t",
            method="GET", path="/x", status_code=500, source="api",
        )
        if created:
            row.created_at = created
        db.add(row)
    db.commit()
    assert cleanup_old_errors(days=30) == 1
    assert len(events(db)) == 1


def test_status_values_are_updated_not_duplicated(db):
    set_status("demo", "one")
    set_status("demo", "two")
    assert get_status("demo")[0] == "two"
    db.expire_all()
    assert len(db.scalars(select(SystemStatus).where(SystemStatus.key == "demo")).all()) == 1