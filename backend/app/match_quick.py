from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select

from app.geo import detect_country
from app.models import Application, Job, Profile, Resume, Swipe
from app.resume_tools import read_pdf_bytes
from app.storage import resume_bytes
from app.routers.resumes import UPLOAD_DIR
from app.skills import extract_skills

MATCH_POOL = 500

# How well a job level fits each experience band (under 1, 1-3, 3-6, 6+ years)
LEVEL_FIT = [
    {"fresher": 10, "junior": 5, "mid": -5, "senior": -15},
    {"fresher": 5, "junior": 10, "mid": 5, "senior": -5},
    {"fresher": -5, "junior": 5, "mid": 10, "senior": 5},
    {"fresher": -10, "junior": -5, "mid": 5, "senior": 10},
]


def resume_skill_set(db, user):
    """Skills found in the user's default resume (lowercase), or None if there is no readable resume."""
    resume = db.scalar(
        select(Resume)
        .where(Resume.user_id == user.id)
        .order_by(Resume.is_default.desc(), Resume.id.desc())
    )
    if resume is None:
        return None
    text = resume.parsed_text or ""
    if not text:
        content = resume_bytes(resume, UPLOAD_DIR)
        if content is not None:
            text, _pages = read_pdf_bytes(content)
            if text:
                resume.parsed_text = text
                db.commit()
    if not text:
        return None
    return {s.lower() for s in extract_skills(text)}


def quick_match(have, job_skills):
    """Percent of the job's listed skills found in the resume. None if the job lists no skills."""
    if not job_skills:
        return None
    matched = sum(1 for s in job_skills if s.lower() in have)
    return round(100 * matched / len(job_skills))


def band(years):
    if years < 1:
        return 0
    if years < 3:
        return 1
    if years < 6:
        return 2
    return 3


@dataclass
class Taste:
    have: set = field(default_factory=set)
    years: float | None = None
    city: str = ""
    country: str | None = None
    liked_skills: set = field(default_factory=set)
    skipped: set = field(default_factory=set)
    applied: set = field(default_factory=set)


def load_taste(db, user):
    taste = Taste()
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile:
        taste.have = {s.lower() for s in (profile.skills or [])}
        taste.years = float(profile.experience_years or 0)
        if profile.location:
            taste.city = profile.location.split(",")[0].strip().lower()
            taste.country = detect_country(profile.location)
    taste.have |= resume_skill_set(db, user) or set()

    swipes = db.execute(select(Swipe.job_id, Swipe.direction).where(Swipe.user_id == user.id)).all()
    liked = [job_id for job_id, direction in swipes if direction == "right"]
    taste.skipped = {job_id for job_id, direction in swipes if direction == "left"}
    taste.applied = set(
        db.scalars(
            select(Application.job_id).where(
                Application.user_id == user.id, Application.status != "saved"
            )
        )
    )
    if liked:
        for skills in db.scalars(select(Job.skills).where(Job.id.in_(liked[-50:]))):
            taste.liked_skills |= {s.lower() for s in (skills or [])}
    return taste


def fit(job, company, taste):
    """Returns (points, reasons). Higher points means a better fit for this user."""
    reasons = []
    points = 0.0
    skills = job.skills or []

    matched = [s for s in skills if s.lower() in taste.have]
    if skills:
        points += 60 * len(matched) / len(skills) + min(len(matched), 5) * 4
    if matched:
        reasons.append("Matches " + ", ".join(matched[:3]))

    if taste.years is not None:
        delta = LEVEL_FIT[band(taste.years)].get(job.experience_level, 0)
        points += delta
        if delta >= 10:
            reasons.append("Fits your experience level")

    where = (job.location or "").lower()
    if taste.city and taste.city in where:
        points += 10
        reasons.append("In " + (job.location or "")[:30])
    elif job.is_remote:
        points += 5
        reasons.append("Remote")
    elif taste.country and job.country == taste.country:
        points += 5

    liked = len({s.lower() for s in skills} & taste.liked_skills)
    points += min(liked * 3, 9)
    if liked >= 2:
        reasons.append("Similar to jobs you liked")

    if company.verification_status == "verified":
        points += 3
    if job.created_at is not None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        points += max(0.0, 5 - (now - job.created_at).days / 6)

    return points, reasons[:3]