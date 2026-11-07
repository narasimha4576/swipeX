import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import Application, ApplicationEvent
from tests.test_recruiter import apply, company, post_job


def get(client, headers, days=30):
    response = client.get("/admin/analytics", params={"days": days}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def last(series):
    return series[-1]["value"]


def set_skills(client, headers, skills):
    client.put("/profile/me", json={"skills": skills}, headers=headers)


def test_analytics_is_for_admins_only(client, seeker, recruiter):
    assert client.get("/admin/analytics").status_code == 401
    assert client.get("/admin/analytics", headers=seeker["headers"]).status_code == 403
    assert client.get("/admin/analytics", headers=recruiter["headers"]).status_code == 403


def test_the_time_range_is_limited(client, admin):
    assert client.get("/admin/analytics", params={"days": 6}, headers=admin["headers"]).status_code == 422
    assert client.get("/admin/analytics", params={"days": 91}, headers=admin["headers"]).status_code == 422


def test_an_empty_platform_gives_zeros_for_every_day(client, admin):
    data = get(client, admin["headers"], days=14)
    for name in ("seekers", "recruiters", "applications", "likes"):
        assert len(data["series"][name]) == 14
        assert all(point["value"] == 0 for point in data["series"][name])
    assert [step["count"] for step in data["funnel"]] == [0, 0, 0, 0, 0, 0]
    assert data["responses"]["answered_percent"] == 0
    assert data["responses"]["average_hours"] is None
    assert data["people_skills"] == [] and data["top_jobs"] == []


def test_todays_signups_are_counted_by_role(client, admin, seeker, recruiter):
    series = get(client, admin["headers"])["series"]
    assert last(series["seekers"]) == 1
    assert last(series["recruiters"]) == 1
    assert series["seekers"][-1]["date"] == datetime.now(timezone.utc).date().isoformat()


def test_the_funnel_follows_a_person_from_signup_to_response(client, db, admin, seeker, make_job, make_resume):
    client.put("/profile/me", json={"headline": "AI engineer"}, headers=seeker["headers"])
    make_resume(seeker["user"]["id"])
    job = make_job()
    client.post("/swipes", json={"job_id": job.id, "direction": "right"}, headers=seeker["headers"])
    resume_id = make_resume(seeker["user"]["id"], name="Second", is_default=False).id
    client.post("/applications/apply", json={"job_id": job.id, "resume_id": resume_id}, headers=seeker["headers"])

    counts = {step["key"]: step["count"] for step in get(client, admin["headers"])["funnel"]}
    assert counts == {
        "registered": 1,
        "profile_started": 1,
        "uploaded_resume": 1,
        "liked_a_job": 1,
        "applied": 1,
        "got_a_response": 0,
    }

    application = db.scalar(select(Application))
    application.status = "shortlisted"
    db.commit()
    from app.cache import clear_cache

    clear_cache()
    funnel = get(client, admin["headers"])["funnel"]
    assert funnel[-1]["count"] == 1 and funnel[-1]["percent"] == 100


def test_applications_per_day_count_each_application_once(client, db, admin, seeker, make_job, make_resume):
    job = make_job()
    resume = make_resume(seeker["user"]["id"])
    client.post("/applications/apply", json={"job_id": job.id, "resume_id": resume.id}, headers=seeker["headers"])
    application = db.scalar(select(Application))
    for status in ("shortlisted", "applied"):  # a recruiter resets it back to applied
        application.status = status
        db.commit()
    assert last(get(client, admin["headers"])["series"]["applications"]) == 1


def test_skills_are_listed_only_when_three_people_share_them(client, admin, register, login):
    for number in range(3):
        email = f"person{number}@example.com"
        register(email)
        skills = ["Python", "Rare Skill"] if number == 0 else ["Python"]
        set_skills(client, login(email), skills)
    skills = dict(get(client, admin["headers"])["people_skills"])
    assert skills == {"python": 3}


def test_job_skills_show_what_employers_ask_for(client, admin, make_job):
    make_job("A", skills=["Python", "SQL"])
    make_job("B", company="Beta Corp", skills=["Python"])
    assert dict(get(client, admin["headers"])["job_skills"]) == {"python": 2, "sql": 1}


def test_most_applied_jobs_and_companies(client, admin, seeker, seeker2, make_job, make_resume):
    job = make_job("Popular Job", company="Busy Co")
    make_job("Quiet Job", company="Calm Co")
    for person in (seeker, seeker2):
        resume = make_resume(person["user"]["id"])
        client.post("/applications/apply", json={"job_id": job.id, "resume_id": resume.id}, headers=person["headers"])
    data = get(client, admin["headers"])
    assert data["top_jobs"] == [{"title": "Popular Job", "company": "Busy Co", "applications": 2}]
    assert data["top_companies"] == [{"company": "Busy Co", "applications": 2}]


def test_response_time_uses_the_first_answer(client, db, admin, recruiter, seeker, make_resume):
    company(client, recruiter["headers"])
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    apply(client, seeker, job_id, make_resume)
    application_id = client.get(f"/recruiter/jobs/{job_id}/applicants", headers=recruiter["headers"]).json()[0][
        "application_id"
    ]
    client.patch(
        f"/recruiter/applications/{application_id}/status", json={"status": "shortlisted"}, headers=recruiter["headers"]
    )
    # pretend the recruiter took 5 hours to answer
    applied = db.scalar(select(ApplicationEvent).where(ApplicationEvent.status == "applied"))
    applied.created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=5)
    db.commit()

    responses = get(client, admin["headers"])["responses"]
    assert responses["applications"] == 1 and responses["answered"] == 1
    assert responses["answered_percent"] == 100
    assert 4.9 <= responses["average_hours"] <= 5.1


def test_nothing_personal_ever_appears(client, admin, seeker, recruiter, make_job, make_resume):
    client.put("/profile/me", json={"headline": "Very Private Headline", "skills": ["Python"]}, headers=seeker["headers"])
    job = make_job()
    resume = make_resume(seeker["user"]["id"], name="Private Resume Name")
    client.post("/applications/apply", json={"job_id": job.id, "resume_id": resume.id}, headers=seeker["headers"])
    text = json.dumps(get(client, admin["headers"]))
    for secret in ("example.com", "Seeker One", "Recruiter One", "Very Private", "Private Resume Name"):
        assert secret not in text