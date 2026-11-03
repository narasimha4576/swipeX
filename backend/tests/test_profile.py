def test_new_profile_starts_empty(client, seeker):
    response = client.get("/profile/me", headers=seeker["headers"])
    assert response.status_code == 200
    assert response.json()["skills"] == []


def test_profile_update_cleans_skills_and_saves(client, seeker):
    response = client.put(
        "/profile/me",
        json={"headline": "AI engineer", "skills": ["Python", " python ", "", "SQL"], "experience_years": 1.5},
        headers=seeker["headers"],
    )
    assert response.status_code == 200
    assert response.json()["skills"] == ["Python", "SQL"]
    again = client.get("/profile/me", headers=seeker["headers"]).json()
    assert again["headline"] == "AI engineer"
    assert again["skills"] == ["Python", "SQL"]


def test_profile_rejects_a_very_long_skill(client, seeker):
    response = client.put("/profile/me", json={"skills": ["x" * 51]}, headers=seeker["headers"])
    assert response.status_code == 422


def test_profile_rejects_negative_experience(client, seeker):
    response = client.put("/profile/me", json={"experience_years": -1}, headers=seeker["headers"])
    assert response.status_code == 422


def experience(**extra):
    data = {
        "company": "Acme",
        "title": "Intern",
        "start_year": 2022,
        "end_year": 2023,
        "description": "Worked on APIs",
    }
    data.update(extra)
    return data


def test_add_list_and_delete_experience(client, seeker):
    created = client.post("/profile/experiences", json=experience(), headers=seeker["headers"])
    assert created.status_code == 201
    listed = client.get("/profile/experiences", headers=seeker["headers"]).json()
    assert [x["title"] for x in listed] == ["Intern"]
    deleted = client.delete(f"/profile/experiences/{created.json()['id']}", headers=seeker["headers"])
    assert deleted.status_code == 204
    assert client.get("/profile/experiences", headers=seeker["headers"]).json() == []


def test_end_year_before_start_year_is_refused(client, seeker):
    response = client.post(
        "/profile/experiences", json=experience(start_year=2022, end_year=2020), headers=seeker["headers"]
    )
    assert response.status_code == 422


def test_experience_can_still_be_current(client, seeker):
    response = client.post("/profile/experiences", json=experience(end_year=None), headers=seeker["headers"])
    assert response.status_code == 201
    assert response.json()["end_year"] is None


def test_nobody_can_delete_someone_elses_experience(client, seeker, seeker2):
    created = client.post("/profile/experiences", json=experience(), headers=seeker["headers"]).json()
    response = client.delete(f"/profile/experiences/{created['id']}", headers=seeker2["headers"])
    assert response.status_code == 404


def test_experience_limit_is_twenty(client, seeker):
    for _ in range(20):
        assert client.post("/profile/experiences", json=experience(), headers=seeker["headers"]).status_code == 201
    assert client.post("/profile/experiences", json=experience(), headers=seeker["headers"]).status_code == 400


def test_portfolio_link_needs_http(client, seeker):
    bad = client.post(
        "/profile/portfolio", json={"title": "Repo", "url": "github.com/me/repo"}, headers=seeker["headers"]
    )
    assert bad.status_code == 422
    good = client.post(
        "/profile/portfolio",
        json={"title": "Repo", "url": "https://github.com/me/repo", "description": "Code"},
        headers=seeker["headers"],
    )
    assert good.status_code == 201


def education(**extra):
    data = {"school": "Siddharth Institute", "degree": "B.Tech", "field_of_study": "AI and ML", "start_year": 2022}
    data.update(extra)
    return data


def test_add_education_and_leave_end_year_empty(client, seeker):
    response = client.post("/profile/educations", json=education(), headers=seeker["headers"])
    assert response.status_code == 201
    assert response.json()["end_year"] is None
    assert len(client.get("/profile/educations", headers=seeker["headers"]).json()) == 1


def test_education_end_year_before_start_is_refused(client, seeker):
    response = client.post(
        "/profile/educations", json=education(start_year=2022, end_year=2020), headers=seeker["headers"]
    )
    assert response.status_code == 422


def test_education_limit_is_ten(client, seeker):
    for _ in range(10):
        assert client.post("/profile/educations", json=education(), headers=seeker["headers"]).status_code == 201
    assert client.post("/profile/educations", json=education(), headers=seeker["headers"]).status_code == 400


def test_nobody_can_delete_someone_elses_education(client, seeker, seeker2):
    created = client.post("/profile/educations", json=education(), headers=seeker["headers"]).json()
    response = client.delete(f"/profile/educations/{created['id']}", headers=seeker2["headers"])
    assert response.status_code == 404