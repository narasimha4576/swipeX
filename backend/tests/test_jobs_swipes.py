def ids(response):
    return {item["id"] for item in response.json()["items"]}


def make_three(make_job):
    python = make_job("Python Backend Developer", skills=["Python", "SQL"])
    react = make_job("React Frontend Engineer", skills=["React", "JavaScript"], is_remote=True, location="Remote")
    intern = make_job(
        "Data Analyst Intern", company="Beta Corp", skills=["SQL", "Excel"], job_type="internship"
    )
    return python, react, intern


def test_jobs_need_a_login(client):
    assert client.get("/jobs").status_code == 401


def test_jobs_list_shows_all_open_jobs(client, seeker, make_job):
    make_three(make_job)
    response = client.get("/jobs", headers=seeker["headers"])
    assert response.status_code == 200
    assert response.json()["total"] == 3


def test_jobs_search_by_text(client, seeker, make_job):
    python, _, _ = make_three(make_job)
    response = client.get("/jobs", params={"q": "python"}, headers=seeker["headers"])
    assert ids(response) == {python.id}


def test_jobs_filter_remote(client, seeker, make_job):
    _, react, _ = make_three(make_job)
    response = client.get("/jobs", params={"remote": "true"}, headers=seeker["headers"])
    assert ids(response) == {react.id}


def test_jobs_filter_by_skill(client, seeker, make_job):
    python, _, intern = make_three(make_job)
    response = client.get("/jobs", params={"skill": "SQL"}, headers=seeker["headers"])
    assert ids(response) == {python.id, intern.id}


def test_jobs_filter_by_job_type(client, seeker, make_job):
    _, _, intern = make_three(make_job)
    response = client.get("/jobs", params={"job_type": "internship"}, headers=seeker["headers"])
    assert ids(response) == {intern.id}


def test_jobs_are_split_into_pages(client, seeker, make_job):
    make_three(make_job)
    first = client.get("/jobs", params={"page": 1, "page_size": 2}, headers=seeker["headers"]).json()
    second = client.get("/jobs", params={"page": 2, "page_size": 2}, headers=seeker["headers"]).json()
    assert first["total"] == 3
    assert len(first["items"]) == 2
    assert len(second["items"]) == 1


def test_jobs_from_rejected_companies_are_hidden(client, seeker, make_job):
    make_job("Fine Job", company="Good Co")
    make_job("Scam Job", company="Bad Co", status="rejected")
    titles = [item["title"] for item in client.get("/jobs", headers=seeker["headers"]).json()["items"]]
    assert titles == ["Fine Job"]


def test_job_detail_and_missing_job(client, seeker, make_job):
    job = make_job("Detail Job")
    assert client.get(f"/jobs/{job.id}", headers=seeker["headers"]).json()["title"] == "Detail Job"
    assert client.get("/jobs/99999", headers=seeker["headers"]).status_code == 404


def test_skills_match_uses_the_default_resume(client, seeker, make_job, make_resume):
    python, react, _ = make_three(make_job)
    make_resume(seeker["user"]["id"], text_content="Experienced in Python and SQL databases and APIs.")
    items = {i["id"]: i for i in client.get("/jobs", headers=seeker["headers"]).json()["items"]}
    assert items[python.id]["match"] == 100
    assert items[react.id]["match"] == 0


def test_no_match_shown_without_a_resume(client, seeker, make_job):
    python, _, _ = make_three(make_job)
    items = {i["id"]: i for i in client.get("/jobs", headers=seeker["headers"]).json()["items"]}
    assert items[python.id]["match"] is None


def test_swiping_right_saves_the_job(client, seeker, make_job):
    job = make_job()
    response = client.post("/swipes", json={"job_id": job.id, "direction": "right"}, headers=seeker["headers"])
    assert response.status_code in (200, 201)
    applications = client.get("/applications", headers=seeker["headers"]).json()
    assert [(a["job"]["id"], a["status"]) for a in applications] == [(job.id, "saved")]


def test_swiped_jobs_leave_the_deck_and_come_back_on_undo(client, seeker, make_job):
    job = make_job()
    deck = client.get("/swipes/deck", headers=seeker["headers"]).json()
    assert [i["id"] for i in deck["items"]] == [job.id]
    client.post("/swipes", json={"job_id": job.id, "direction": "left"}, headers=seeker["headers"])
    assert client.get("/swipes/deck", headers=seeker["headers"]).json()["items"] == []
    undo = client.delete(f"/swipes/{job.id}", headers=seeker["headers"])
    assert undo.status_code in (200, 204)
    assert [i["id"] for i in client.get("/swipes/deck", headers=seeker["headers"]).json()["items"]] == [job.id]


def test_recruiters_cannot_swipe(client, recruiter, make_job):
    job = make_job()
    response = client.post("/swipes", json={"job_id": job.id, "direction": "right"}, headers=recruiter["headers"])
    assert response.status_code == 403


def test_applying_counts_the_applicant(client, seeker, make_job, make_resume):
    job = make_job()
    resume = make_resume(seeker["user"]["id"])
    response = client.post(
        "/applications/apply", json={"job_id": job.id, "resume_id": resume.id}, headers=seeker["headers"]
    )
    assert response.status_code in (200, 201)
    assert client.get(f"/jobs/{job.id}", headers=seeker["headers"]).json()["applicant_count"] == 1
    applications = client.get("/applications", headers=seeker["headers"]).json()
    assert [(a["job"]["id"], a["status"]) for a in applications] == [(job.id, "applied")]


def test_cannot_apply_with_someone_elses_resume(client, seeker, seeker2, make_job, make_resume):
    job = make_job()
    other = make_resume(seeker2["user"]["id"])
    response = client.post(
        "/applications/apply", json={"job_id": job.id, "resume_id": other.id}, headers=seeker["headers"]
    )
    assert response.status_code in (400, 403, 404)
    assert client.get(f"/jobs/{job.id}", headers=seeker["headers"]).json()["applicant_count"] == 0