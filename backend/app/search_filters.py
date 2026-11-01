from datetime import datetime, timedelta, timezone

from sqlalchemy import Text, and_, cast, or_

from app.models import Company, Job

LOW_COMPETITION_MAX = 60


def build_conditions(f):
    conditions = [Job.is_active.is_(True)]
    if f.get("verified_only"):
        conditions.append(Company.verification_status == "verified")
    else:
        conditions.append(Company.verification_status != "rejected")

    q = (f.get("q") or "").strip()
    if q:
        pattern = f"%{q}%"
        conditions.append(
            or_(
                Job.title.ilike(pattern),
                Company.name.ilike(pattern),
                cast(Job.skills, Text).ilike(pattern),
            )
        )
    if f.get("company_type"):
        conditions.append(Company.company_type == f["company_type"])
    if f.get("job_type"):
        conditions.append(Job.job_type == f["job_type"])
    if f.get("experience_level"):
        conditions.append(Job.experience_level == f["experience_level"])
    if f.get("remote"):
        conditions.append(Job.is_remote.is_(True))

    country = (f.get("country") or "").strip()
    if country:
        conditions.append(
            or_(Job.country == country, and_(Job.is_remote.is_(True), Job.country.is_(None)))
        )
    location = (f.get("location") or "").strip()
    if location:
        conditions.append(Job.location.ilike(f"%{location}%"))
    skill = (f.get("skill") or "").strip().replace('"', "")
    if skill:
        conditions.append(cast(Job.skills, Text).ilike(f'%"{skill}"%'))
    if f.get("min_salary") is not None:
        conditions.append(Job.salary_max_lpa >= f["min_salary"])
    if f.get("max_age_days"):
        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=f["max_age_days"])
        conditions.append(Job.created_at >= since)
    if f.get("fresher_friendly"):
        conditions.append(
            or_(
                Job.experience_level == "fresher",
                Job.job_type.in_(["internship", "apprenticeship"]),
            )
        )
    if f.get("low_competition"):
        conditions.append(Job.applicant_count < LOW_COMPETITION_MAX)
        conditions.append(Job.source == "native")
    return conditions