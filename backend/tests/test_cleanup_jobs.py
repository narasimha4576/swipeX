from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.importers.cleanup_jobs import cleanup_old_jobs
from app.models import Job


def age(db, job, days=90, active=False, source="greenhouse"):
    job.is_active = active
    job.source = source
    job.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    db.commit()


def titles(db):
    db.expire_all()
    return {job.title for job in db.scalars(select(Job))}


def test_an_old_closed_imported_job_is_removed(db, make_job):
    age(db, make_job("Old closed"))
    assert cleanup_old_jobs() == 1
    assert titles(db) == set()


def test_open_jobs_are_never_removed(db, make_job):
    age(db, make_job("Old but open"), active=True)
    assert cleanup_old_jobs() == 0
    assert titles(db) == {"Old but open"}


def test_recently_closed_jobs_stay(db, make_job):
    age(db, make_job("Closed last week"), days=7)
    assert cleanup_old_jobs() == 0


def test_jobs_posted_on_swipex_stay(db, make_job):
    age(db, make_job("Posted by a recruiter"), source="native")
    assert cleanup_old_jobs() == 0


def test_jobs_people_liked_stay(client, db, seeker, make_job):
    job = make_job("Somebody liked this")
    client.post("/swipes", json={"job_id": job.id, "direction": "right"}, headers=seeker["headers"])
    age(db, job)
    assert cleanup_old_jobs() == 0
    assert titles(db) == {"Somebody liked this"}


def test_the_time_limit_can_be_changed(db, make_job, monkeypatch):
    age(db, make_job("Forty days old"), days=40)
    assert cleanup_old_jobs() == 0
    monkeypatch.setenv("JOB_RETENTION_DAYS", "30")
    assert cleanup_old_jobs() == 1