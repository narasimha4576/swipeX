import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text, update
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

# Point the whole app at a separate test database BEFORE the app is imported.
TEST_DB_NAME = "swipex_test"
_dev_url = make_url(os.environ["DATABASE_URL"])
os.environ["DATABASE_URL"] = _dev_url.set(database=TEST_DB_NAME).render_as_string(hide_password=False)
os.environ["IMPORT_ENABLED"] = "false"


def _ensure_test_database():
    admin_engine = create_engine(_dev_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB_NAME})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()


_ensure_test_database()

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Company, Job, Resume, User  # noqa: E402
from app.security import hash_password  # noqa: E402

if engine.url.database != TEST_DB_NAME:
    raise RuntimeError("Tests may only run on the test database. Stopping to protect your data.")
Base.metadata.create_all(engine)

PASSWORD = "Passw0rd!123"


@pytest.fixture(autouse=True)
def clean_db():
    """Every test starts with empty tables."""
    with engine.begin() as conn:
        names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def register(client):
    def _register(email, role="job_seeker", name="Test Person", password=PASSWORD):
        response = client.post(
            "/auth/register",
            json={"email": email, "password": password, "full_name": name, "role": role},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _register


@pytest.fixture
def login(client):
    def _login(email, password=PASSWORD):
        response = client.post("/auth/login", data={"username": email, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login


@pytest.fixture
def seeker(register, login):
    user = register("seeker@example.com", name="Seeker One")
    return {"user": user, "headers": login("seeker@example.com")}


@pytest.fixture
def seeker2(register, login):
    user = register("seeker2@example.com", name="Seeker Two")
    return {"user": user, "headers": login("seeker2@example.com")}


@pytest.fixture
def recruiter(register, login):
    user = register("recruiter@example.com", role="recruiter", name="Recruiter One")
    return {"user": user, "headers": login("recruiter@example.com")}


@pytest.fixture
def admin(db, login):
    user = User(
        email="admin@example.com",
        password_hash=hash_password(PASSWORD),
        full_name="Admin Person",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user": {"id": user.id, "email": user.email}, "headers": login("admin@example.com")}


@pytest.fixture
def make_job(db):
    def _make(
        title="Python Developer",
        company="Acme Labs",
        skills=None,
        is_remote=False,
        location="Bengaluru, India",
        job_type="full_time",
        level="fresher",
        status="verified",
    ):
        owner = db.scalar(select(Company).where(Company.name == company))
        if owner is None:
            owner = Company(name=company, company_type="startup", verification_status=status)
            db.add(owner)
            db.commit()
            db.refresh(owner)
        job = Job(
            company_id=owner.id,
            title=title,
            description="A good role for a careful person who likes to learn. " * 3,
            location=location,
            is_remote=is_remote,
            job_type=job_type,
            experience_level=level,
            skills=skills or ["Python"],
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    return _make


@pytest.fixture
def make_resume(db):
    def _make(user_id, name="Main resume", text_content=None, is_default=True):
        resume = Resume(
            user_id=user_id,
            version_name=name,
            file_path=f"test-{user_id}.pdf",
            parsed_text=text_content,
            is_default=is_default,
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        return resume

    return _make


@pytest.fixture
def disable_user(db):
    def _disable(email):
        db.execute(update(User).where(User.email == email).values(is_active=False))
        db.commit()

    return _disable

@pytest.fixture
def recruiter2(register, login):
    user = register("recruiter2@example.com", role="recruiter", name="Recruiter Two")
    return {"user": user, "headers": login("recruiter2@example.com")}

@pytest.fixture(autouse=True)
def reset_in_memory_limits():
    """Rate limits are remembered in memory, so every test starts with a clean slate."""
    from app.routers import team

    team._attempts.clear()
    yield

@pytest.fixture(autouse=True)
def reset_security_limits():
    from app.ratelimit import reset_all_limiters

    reset_all_limiters()
    yield


@pytest.fixture(autouse=True)
def temp_uploads(tmp_path, monkeypatch):
    """Resumes and photos made by tests go to a temporary folder that is deleted afterwards."""
    import importlib

    folder = tmp_path / "uploads"
    folder.mkdir()
    for name in ("app.routers.resumes", "app.routers.recruiter", "app.routers.resume_ai", "app.match_quick"):
        module = importlib.import_module(name)
        if hasattr(module, "UPLOAD_DIR"):
            monkeypatch.setattr(module, "UPLOAD_DIR", folder)
    extras = importlib.import_module("app.routers.profile_extras")
    photos = folder / "photos"
    photos.mkdir()
    monkeypatch.setattr(extras, "PHOTO_DIR", photos)
    yield

@pytest.fixture(autouse=True)
def empty_cache():
    from app.cache import clear_cache

    clear_cache()
    yield