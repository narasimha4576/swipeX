import pytest


def company(client, headers, name="Hiring Co"):
    response = client.put("/recruiter/company", json={"name": name, "company_type": "startup"}, headers=headers)
    assert response.status_code in (200, 201), response.text
    return response.json()


def job_payload(**extra):
    data = {
        "title": "Backend Engineer",
        "description": "Build and run our APIs with Python and FastAPI. Work with a friendly team.",
        "location": "Bengaluru",
        "is_remote": False,
        "job_type": "full_time",
        "experience_level": "fresher",
        "salary_min_lpa": 4,
        "salary_max_lpa": 8,
        "skills": ["Python", "FastAPI"],
    }
    data.update(extra)
    return data


def post_job(client, headers, **extra):
    return client.post("/recruiter/jobs", json=job_payload(**extra), headers=headers)


def apply(client, seeker, job_id, make_resume):
    resume = make_resume(seeker["user"]["id"])
    response = client.post(
        "/applications/apply", json={"job_id": job_id, "resume_id": resume.id}, headers=seeker["headers"]
    )
    assert response.status_code in (200, 201), response.text


def test_cannot_post_a_job_before_setting_up_a_company(client, recruiter):
    assert post_job(client, recruiter["headers"]).status_code == 400


def test_recruiter_posts_a_job_and_sees_it(client, recruiter):
    company(client, recruiter["headers"])
    response = post_job(client, recruiter["headers"])
    assert response.status_code in (200, 201), response.text
    jobs = client.get("/recruiter/jobs", headers=recruiter["headers"]).json()
    assert [j["title"] for j in jobs] == ["Backend Engineer"]


def test_posted_job_appears_for_job_seekers(client, recruiter, seeker):
    company(client, recruiter["headers"])
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    response = client.get(f"/jobs/{job_id}", headers=seeker["headers"])
    assert response.status_code == 200
    assert response.json()["title"] == "Backend Engineer"


def test_scam_wording_is_blocked(client, recruiter):
    company(client, recruiter["headers"])
    response = post_job(
        client,
        recruiter["headers"],
        description="Great job! Pay a registration fee of 2000 rupees to confirm your selection today.",
    )
    assert response.status_code == 400


def test_only_recruiters_can_post_jobs(client, seeker):
    assert post_job(client, seeker["headers"]).status_code == 403


def test_edit_a_job(client, recruiter, seeker):
    company(client, recruiter["headers"])
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    response = client.patch(
        f"/recruiter/jobs/{job_id}",
        json=job_payload(title="Senior Backend Engineer", skills=["Python", "Docker"]),
        headers=recruiter["headers"],
    )
    assert response.status_code == 200, response.text
    seen = client.get(f"/jobs/{job_id}", headers=seeker["headers"]).json()
    assert seen["title"] == "Senior Backend Engineer"
    assert seen["skills"] == ["Python", "Docker"]


def test_edit_cannot_add_scam_wording(client, recruiter):
    company(client, recruiter["headers"])
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    response = client.patch(
        f"/recruiter/jobs/{job_id}",
        json=job_payload(description="Send a registration fee of 2000 rupees to get the job offer now."),
        headers=recruiter["headers"],
    )
    assert response.status_code == 400


def test_another_company_cannot_edit_my_job(client, recruiter, recruiter2):
    company(client, recruiter["headers"])
    company(client, recruiter2["headers"], name="Other Co")
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    response = client.patch(
        f"/recruiter/jobs/{job_id}", json=job_payload(title="Hijacked"), headers=recruiter2["headers"]
    )
    assert response.status_code == 404


def test_each_company_only_sees_its_own_jobs(client, recruiter, recruiter2):
    company(client, recruiter["headers"])
    company(client, recruiter2["headers"], name="Other Co")
    post_job(client, recruiter["headers"], title="Mine")
    assert client.get("/recruiter/jobs", headers=recruiter2["headers"]).json() == []


def test_recruiter_sees_applicants(client, recruiter, seeker, make_resume):
    company(client, recruiter["headers"])
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    apply(client, seeker, job_id, make_resume)
    applicants = client.get(f"/recruiter/jobs/{job_id}/applicants", headers=recruiter["headers"]).json()
    assert [a["full_name"] for a in applicants] == ["Seeker One"]
    assert applicants[0]["status"] == "applied"


def test_another_company_cannot_see_my_applicants(client, recruiter, recruiter2, seeker, make_resume):
    company(client, recruiter["headers"])
    company(client, recruiter2["headers"], name="Other Co")
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    apply(client, seeker, job_id, make_resume)
    response = client.get(f"/recruiter/jobs/{job_id}/applicants", headers=recruiter2["headers"])
    assert response.status_code == 404


@pytest.mark.parametrize(
    "status,label",
    [("shortlisted", "Shortlisted"), ("interview", "Interview"), ("rejected", "Rejected")],
)
def test_status_change_notifies_the_applicant(client, recruiter, seeker, make_resume, status, label):
    company(client, recruiter["headers"])
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    apply(client, seeker, job_id, make_resume)
    application_id = client.get(f"/recruiter/jobs/{job_id}/applicants", headers=recruiter["headers"]).json()[0][
        "application_id"
    ]
    response = client.patch(
        f"/recruiter/applications/{application_id}/status", json={"status": status}, headers=recruiter["headers"]
    )
    assert response.status_code == 200, response.text
    data = client.get("/notifications", headers=seeker["headers"]).json()
    assert data["unread"] == 1
    assert data["items"][0]["title"] == f"Hiring Co: {label}"
    assert data["items"][0]["link"] == "/applications"


def test_reset_to_applied_does_not_notify(client, recruiter, seeker, make_resume):
    company(client, recruiter["headers"])
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    apply(client, seeker, job_id, make_resume)
    application_id = client.get(f"/recruiter/jobs/{job_id}/applicants", headers=recruiter["headers"]).json()[0][
        "application_id"
    ]
    for status in ("shortlisted", "applied"):
        client.patch(
            f"/recruiter/applications/{application_id}/status", json={"status": status}, headers=recruiter["headers"]
        )
    assert len(client.get("/notifications", headers=seeker["headers"]).json()["items"]) == 1