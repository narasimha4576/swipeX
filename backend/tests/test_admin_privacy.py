import json


def build_private_life(client, seeker, make_job, make_resume):
    """Gives the seeker lots of private data, then returns the secret words used."""
    headers = seeker["headers"]
    client.put(
        "/profile/me",
        json={"headline": "SECRET-HEADLINE", "bio": "SECRET-BIO", "skills": ["SecretSkill"], "location": "SECRET-CITY"},
        headers=headers,
    )
    client.post(
        "/profile/experiences",
        json={"company": "SecretCorp", "title": "SecretTitle", "start_year": 2021},
        headers=headers,
    )
    client.post(
        "/profile/educations",
        json={"school": "SecretSchool", "degree": "B.Tech", "start_year": 2022},
        headers=headers,
    )
    client.post(
        "/profile/portfolio",
        json={"title": "SecretRepo", "url": "https://example.com/secret-repo"},
        headers=headers,
    )
    resume = make_resume(seeker["user"]["id"], name="SecretResumeName")
    job = make_job("SecretJobTitle", company="SecretCompany")
    client.post("/applications/apply", json={"job_id": job.id, "resume_id": resume.id}, headers=headers)
    return resume


def test_admin_detail_hides_private_data(client, admin, seeker, make_job, make_resume):
    build_private_life(client, seeker, make_job, make_resume)
    response = client.get(f"/admin/users/{seeker['user']['id']}/detail", headers=admin["headers"])
    assert response.status_code == 200
    body = json.dumps(response.json())
    assert "secret" not in body.lower()
    assert "profile" not in response.json()
    assert "photo_url" not in response.json()


def test_admin_detail_shows_account_basics_and_counts(client, admin, seeker, make_job, make_resume):
    build_private_life(client, seeker, make_job, make_resume)
    data = client.get(f"/admin/users/{seeker['user']['id']}/detail", headers=admin["headers"]).json()
    assert data["account"]["email"] == "seeker@example.com"
    assert data["account"]["role"] == "job_seeker"
    assert data["summary"]["resumes"] == 1
    assert data["summary"]["applications"] == 1
    assert data["summary"]["profile_completeness_percent"] == 100


def test_admin_detail_for_a_recruiter_shows_company_and_counts(client, admin, recruiter):
    saved = client.put(
        "/recruiter/company",
        json={"name": "Hiring Co", "company_type": "startup"},
        headers=recruiter["headers"],
    )
    assert saved.status_code in (200, 201)
    data = client.get(f"/admin/users/{recruiter['user']['id']}/detail", headers=admin["headers"]).json()
    assert data["company"]["name"] == "Hiring Co"
    assert data["summary"]["team_members"] == 1
    assert data["summary"]["jobs_posted"] == 0


def test_admin_cannot_download_resumes(client, admin, seeker, make_resume):
    resume = make_resume(seeker["user"]["id"])
    response = client.get(f"/admin/resumes/{resume.id}/file", headers=admin["headers"])
    assert response.status_code in (404, 405)


def test_admin_overview_has_no_personal_lists(client, admin, seeker):
    data = client.get("/admin/overview", headers=admin["headers"]).json()
    assert "recent_applications" not in data
    assert all("email" not in person for person in data["recent_signups"])
    assert data["users_by_role"]["job_seeker"] == 1


def test_opening_an_account_is_written_to_the_activity_log(client, admin, seeker):
    client.get(f"/admin/users/{seeker['user']['id']}/detail", headers=admin["headers"])
    log = client.get("/admin/overview", headers=admin["headers"]).json()["activity_log"]
    assert log[0]["action"] == "viewed_account"
    assert log[0]["target"] == "Seeker One"
    assert log[0]["admin"] == "Admin Person"


def test_disabling_an_account_is_logged(client, admin, seeker):
    client.patch(
        f"/admin/users/{seeker['user']['id']}/active", params={"is_active": "false"}, headers=admin["headers"]
    )
    log = client.get("/admin/overview", headers=admin["headers"]).json()["activity_log"]
    assert log[0]["action"] == "disabled_account"


def test_normal_users_cannot_use_the_admin_views(client, seeker, recruiter):
    for headers in (seeker["headers"], recruiter["headers"]):
        assert client.get(f"/admin/users/{seeker['user']['id']}/detail", headers=headers).status_code == 403
        assert client.get("/admin/overview", headers=headers).status_code == 403