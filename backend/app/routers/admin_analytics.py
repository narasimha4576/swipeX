from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.cache import cached
from app.deps import get_db, require_roles
from app.models import User

router = APIRouter(prefix="/admin", tags=["admin-analytics"])
admin_only = require_roles("admin")

# A skill is only listed when at least this many people have it, so a list can never point at one person.
MIN_GROUP = 3

FUNNEL = [
    ("registered", "Signed up as a job seeker", "SELECT count(*) FROM users WHERE role = 'job_seeker'"),
    (
        "profile_started",
        "Started a profile (headline or skills)",
        "SELECT count(*) FROM profiles p JOIN users u ON u.id = p.user_id WHERE u.role = 'job_seeker' AND "
        "((json_typeof(p.skills) = 'array' AND json_array_length(p.skills) > 0) OR coalesce(p.headline, '') <> '')",
    ),
    ("uploaded_resume", "Uploaded a resume", "SELECT count(DISTINCT user_id) FROM resumes"),
    ("liked_a_job", "Liked at least one job", "SELECT count(DISTINCT user_id) FROM swipes WHERE direction = 'right'"),
    ("applied", "Applied to a job", "SELECT count(DISTINCT user_id) FROM applications WHERE status <> 'saved'"),
    (
        "got_a_response",
        "Was shortlisted or invited to interview",
        "SELECT count(DISTINCT user_id) FROM applications WHERE status IN ('shortlisted', 'interview')",
    ),
]


def build(db: Session, days: int):
    today = datetime.now(timezone.utc).replace(tzinfo=None).date()
    start = today - timedelta(days=days - 1)
    params = {"start": datetime.combine(start, datetime.min.time())}

    def per_day(sql, **extra):
        rows = db.execute(text(sql), {**params, **extra}).all()
        counts = {row[0]: row[1] for row in rows}
        return [
            {"date": (start + timedelta(days=i)).isoformat(), "value": counts.get(start + timedelta(days=i), 0)}
            for i in range(days)
        ]

    series = {
        "seekers": per_day(
            "SELECT CAST(created_at AS date), count(*) FROM users "
            "WHERE role = 'job_seeker' AND created_at >= :start GROUP BY 1"
        ),
        "recruiters": per_day(
            "SELECT CAST(created_at AS date), count(*) FROM users "
            "WHERE role = 'recruiter' AND created_at >= :start GROUP BY 1"
        ),
        "applications": per_day(
            "SELECT CAST(first_applied AS date), count(*) FROM ("
            "SELECT application_id, min(created_at) AS first_applied FROM application_events "
            "WHERE status = 'applied' GROUP BY application_id) t "
            "WHERE first_applied >= :start GROUP BY 1"
        ),
        "likes": per_day(
            "SELECT CAST(updated_at AS date), count(*) FROM swipes "
            "WHERE direction = 'right' AND updated_at >= :start GROUP BY 1"
        ),
    }

    funnel = []
    first = None
    for key, label, sql in FUNNEL:
        number = db.execute(text(sql)).scalar() or 0
        first = number if first is None else first
        funnel.append(
            {"key": key, "label": label, "count": number, "percent": round(100 * number / first) if first else 0}
        )

    def pairs(sql, **extra):
        return [[row[0], row[1]] for row in db.execute(text(sql), extra).all()]

    people_skills = pairs(
        "SELECT lower(s), count(DISTINCT p.user_id) FROM profiles p, json_array_elements_text(p.skills) AS s "
        "WHERE json_typeof(p.skills) = 'array' GROUP BY 1 HAVING count(DISTINCT p.user_id) >= :minimum "
        "ORDER BY 2 DESC, 1 LIMIT 15",
        minimum=MIN_GROUP,
    )
    job_skills = pairs(
        "SELECT lower(s), count(*) FROM jobs j, json_array_elements_text(j.skills) AS s "
        "WHERE j.is_active AND json_typeof(j.skills) = 'array' GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 15"
    )

    top_jobs = [
        {"title": row[0], "company": row[1], "applications": row[2]}
        for row in db.execute(
            text(
                "SELECT j.title, c.name, count(a.id) FROM applications a JOIN jobs j ON j.id = a.job_id "
                "JOIN companies c ON c.id = j.company_id WHERE a.status <> 'saved' "
                "GROUP BY j.id, j.title, c.name ORDER BY 3 DESC, j.id LIMIT 10"
            )
        ).all()
    ]
    top_companies = [
        {"company": row[0], "applications": row[1]}
        for row in db.execute(
            text(
                "SELECT c.name, count(a.id) FROM applications a JOIN jobs j ON j.id = a.job_id "
                "JOIN companies c ON c.id = j.company_id WHERE a.status <> 'saved' "
                "GROUP BY c.id, c.name ORDER BY 2 DESC, c.id LIMIT 10"
            )
        ).all()
    ]

    applied_total = (
        db.execute(
            text("SELECT count(DISTINCT application_id) FROM application_events WHERE status = 'applied'")
        ).scalar()
        or 0
    )
    answered = db.execute(
        text(
            "SELECT count(*), avg(extract(epoch FROM (r.responded - a.applied)) / 3600.0) FROM "
            "(SELECT application_id, min(created_at) AS applied FROM application_events "
            "WHERE status = 'applied' GROUP BY application_id) a JOIN "
            "(SELECT application_id, min(created_at) AS responded FROM application_events "
            "WHERE status IN ('shortlisted', 'interview', 'rejected') GROUP BY application_id) r "
            "ON r.application_id = a.application_id WHERE r.responded >= a.applied"
        )
    ).one()
    answered_total = answered[0] or 0

    jobs = {
        "open": db.execute(text("SELECT count(*) FROM jobs WHERE is_active")).scalar() or 0,
        "by_source": pairs("SELECT source, count(*) FROM jobs WHERE is_active GROUP BY 1 ORDER BY 2 DESC LIMIT 8"),
        "by_country": pairs(
            "SELECT country, count(*) FROM jobs WHERE is_active AND country IS NOT NULL "
            "GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
        ),
    }

    return jsonable_encoder(
        {
            "days": days,
            "series": series,
            "funnel": funnel,
            "people_skills": people_skills,
            "job_skills": job_skills,
            "min_group": MIN_GROUP,
            "top_jobs": top_jobs,
            "top_companies": top_companies,
            "responses": {
                "applications": applied_total,
                "answered": answered_total,
                "answered_percent": round(100 * answered_total / applied_total) if applied_total else 0,
                "average_hours": round(float(answered[1]), 1) if answered[1] is not None else None,
            },
            "jobs": jobs,
        }
    )


@router.get("/analytics")
def analytics(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    """Counts only. No names, emails or profile contents ever appear here."""
    return cached(f"analytics:{days}", 60, lambda: build(db, days))