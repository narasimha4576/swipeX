from sqlalchemy import select

from app.models import Resume
from app.resume_tools import read_pdf
from app.routers.resumes import UPLOAD_DIR
from app.skills import extract_skills


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
        path = UPLOAD_DIR / resume.file_path
        if path.exists():
            text, _pages = read_pdf(path)
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