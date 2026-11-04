import io
import zipfile

import pytest

import app.routers.resumes as resumes_module
from app.models import (
    Application,
    ApplicationEvent,
    Education,
    Experience,
    Job,
    Notification,
    PortfolioItem,
    Profile,
    Resume,
    SavedSearch,
    Swipe,
)
from sqlalchemy import func, select
from tests.conftest import PASSWORD
from tests.test_profile_extras import png_bytes
from tests.test_recruiter import company, post_job
from tests.test_security import make_pdf, upload
from tests.test_team import make_team


def open_export(client, headers):
    response = client.get("/account/export", headers=headers)
    assert response.status_code == 200, response.text
    return zipfile.ZipFile(io.BytesIO(response.content))


def delete_me(client, headers, password=PASSWORD, confirm="DELETE"):
    return client.post("/account/delete", json={"password": password, "confirm": confirm}, headers=headers)


def fill_seeker_life(client, seeker, job_id=None):
    """Gives a job seeker data in every part of the app."""
    h = seeker["headers"]
    client.put("/profile/me", json={"headline": "AI engineer", "bio": "My private bio", "skills": ["Python"]}, headers=h)
    client.post("/profile/experiences", json={"company": "Acme", "title": "Intern", "start_year": 2022}, headers=h)
    client.post("/profile/educations", json={"school": "My College", "degree": "B.Tech", "start_year": 2022}, headers=h)
    client.post("/profile/portfolio", json={"title": "Repo", "url": "https://github.com/me/repo"}, headers=h)
    client.post("/saved-searches", json={"name": "Python", "filters": {"q": "python"}}, headers=h)
    photo = client.post("/profile/photo", files={"file": ("me.png", png_bytes(), "image/png")}, headers=h).json()
    slug = client.put("/profile/public", json={"enabled": True}, headers=h).json()["slug"]
    resume_id = upload(client, h, make_pdf()).json()["id"]
    if job_id:
        client.post("/applications/apply", json={"job_id": job_id, "resume_id": resume_id}, headers=h)
    return {"photo_url": photo["photo_url"], "slug": slug, "resume_id": resume_id}


def count(db, model, user_id):
    return db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id))


# ---------- download my data ----------


def test_export_needs_a_login(client):
    assert client.get("/account/export").status_code == 401


def test_export_holds_my_data_and_my_files(client, seeker):
    fill_seeker_life(client, seeker)
    bundle = open_export(client, seeker["headers"])
    names = bundle.namelist()
    assert "data.json" in names and "README.txt" in names and "photo.jpg" in names
    assert any(n.startswith("resumes/") and n.endswith(".pdf") for n in names)

    raw = bundle.read("data.json").decode("utf-8")
    assert "password" not in raw.lower()
    import json

    data = json.loads(raw)
    assert data["account"]["email"] == "seeker@example.com"
    assert data["profile"]["headline"] == "AI engineer"
    assert data["experiences"][0]["company"] == "Acme"
    assert data["educations"][0]["school"] == "My College"
    assert data["portfolio"][0]["title"] == "Repo"
    assert data["saved_searches"][0]["name"] == "Python"
    assert data["resumes"][0]["name"] == "Main"


def test_export_never_holds_other_peoples_data(client, seeker, seeker2):
    client.put("/profile/me", json={"bio": "SECOND-PERSON-SECRET"}, headers=seeker2["headers"])
    fill_seeker_life(client, seeker)
    raw = open_export(client, seeker["headers"]).read("data.json").decode("utf-8")
    assert "SECOND-PERSON-SECRET" not in raw
    assert "seeker2@example.com" not in raw


def test_recruiter_export_has_company_and_jobs(client, recruiter):
    company(client, recruiter["headers"])
    post_job(client, recruiter["headers"], title="Backend Engineer")
    import json

    data = json.loads(open_export(client, recruiter["headers"]).read("data.json").decode("utf-8"))
    assert data["company"]["name"] == "Hiring Co"
    assert data["team_role"] == "owner"
    assert [j["title"] for j in data["jobs_posted"]] == ["Backend Engineer"]


def test_export_is_limited_to_five_an_hour(client, seeker):
    for _ in range(5):
        assert client.get("/account/export", headers=seeker["headers"]).status_code == 200
    assert client.get("/account/export", headers=seeker["headers"]).status_code == 429


# ---------- delete my account ----------


def test_delete_needs_the_right_password_and_the_word_delete(client, seeker):
    assert delete_me(client, seeker["headers"], password="Wrong-password-1").status_code == 400
    assert delete_me(client, seeker["headers"], confirm="yes please").status_code == 400
    assert client.get("/auth/me", headers=seeker["headers"]).status_code == 200


def test_wrong_passwords_are_limited(client, seeker):
    for _ in range(5):
        assert delete_me(client, seeker["headers"], password="Wrong-password-1").status_code == 400
    assert delete_me(client, seeker["headers"]).status_code == 429
    assert client.get("/auth/me", headers=seeker["headers"]).status_code == 200


def test_deleting_removes_everything_of_a_job_seeker(client, db, seeker, seeker2, recruiter):
    company(client, recruiter["headers"])
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    made = fill_seeker_life(client, seeker, job_id=job_id)
    client.post("/swipes", json={"job_id": job_id, "direction": "right"}, headers=seeker["headers"])
    user_id = seeker["user"]["id"]

    application_id = client.get(f"/recruiter/jobs/{job_id}/applicants", headers=recruiter["headers"]).json()[0][
        "application_id"
    ]
    client.patch(
        f"/recruiter/applications/{application_id}/status",
        json={"status": "shortlisted"},
        headers=recruiter["headers"],
    )
    assert count(db, Notification, user_id) >= 1

    assert delete_me(client, seeker["headers"]).status_code == 204

    # the account itself
    assert client.post("/auth/login", data={"username": "seeker@example.com", "password": PASSWORD}).status_code == 401
    assert client.get("/auth/me", headers=seeker["headers"]).status_code == 401
    # every kind of personal data
    db.expire_all()
    for model in (Profile, Experience, Education, PortfolioItem, Resume, Application, Swipe, SavedSearch, Notification):
        assert count(db, model, user_id) == 0, model.__name__
    assert db.scalar(select(func.count()).select_from(ApplicationEvent)) == 0
    # files and public pages
    assert not list(resumes_module.UPLOAD_DIR.glob("*.pdf"))
    assert client.get(made["photo_url"]).status_code == 404
    assert client.get(f"/public/profiles/{made['slug']}").status_code == 404
    # the job and its applicant count stay, the applicant is gone
    assert client.get(f"/jobs/{job_id}", headers=seeker2["headers"]).json()["applicant_count"] == 1
    assert client.get(f"/recruiter/jobs/{job_id}/applicants", headers=recruiter["headers"]).json() == []


def test_other_peoples_data_survives_a_deletion(client, seeker, seeker2):
    client.put("/profile/me", json={"headline": "Still here"}, headers=seeker2["headers"])
    fill_seeker_life(client, seeker)
    assert delete_me(client, seeker["headers"]).status_code == 204
    assert client.get("/profile/me", headers=seeker2["headers"]).json()["headline"] == "Still here"


def test_the_same_email_can_sign_up_again(client, register, seeker):
    assert delete_me(client, seeker["headers"]).status_code == 204
    assert register("seeker@example.com")["email"] == "seeker@example.com"


def test_a_team_member_can_delete_and_the_company_keeps_the_jobs(client, recruiter, recruiter2):
    make_team(client, recruiter, recruiter2)
    job_id = post_job(client, recruiter2["headers"], title="Posted by member").json()["id"]
    assert delete_me(client, recruiter2["headers"]).status_code == 204

    jobs = client.get("/recruiter/jobs", headers=recruiter["headers"]).json()
    assert [(j["id"], j["is_active"]) for j in jobs] == [(job_id, True)]
    assert len(client.get("/recruiter/team", headers=recruiter["headers"]).json()["members"]) == 1


def test_a_lone_owner_deleting_closes_jobs_but_applicants_keep_their_history(client, db, recruiter, seeker):
    company(client, recruiter["headers"])
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    fill_seeker_life(client, seeker, job_id=job_id)
    assert delete_me(client, recruiter["headers"]).status_code == 204

    db.expire_all()
    job = db.get(Job, job_id)
    assert job.is_active is False
    assert job.posted_by is None
    applications = client.get("/applications", headers=seeker["headers"]).json()
    assert [a["job"]["id"] for a in applications] == [job_id]


def test_an_owner_with_a_team_must_remove_the_team_first(client, recruiter, recruiter2):
    make_team(client, recruiter, recruiter2)
    assert delete_me(client, recruiter["headers"]).status_code == 400
    assert client.get("/auth/me", headers=recruiter["headers"]).status_code == 200


def test_admin_accounts_are_not_deleted_from_the_website(client, admin):
    assert delete_me(client, admin["headers"]).status_code == 403
    assert client.get("/auth/me", headers=admin["headers"]).status_code == 200