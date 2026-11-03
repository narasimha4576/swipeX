from tests.test_recruiter import apply, company, job_payload, post_job


def make_team(client, recruiter, recruiter2):
    company(client, recruiter["headers"])
    code = client.get("/recruiter/team", headers=recruiter["headers"]).json()["invite_code"]
    response = client.post("/recruiter/team/join", json={"code": code}, headers=recruiter2["headers"])
    assert response.status_code == 200, response.text
    return code


def test_owner_gets_an_invite_code(client, recruiter):
    company(client, recruiter["headers"])
    team = client.get("/recruiter/team", headers=recruiter["headers"]).json()
    assert team["company_name"] == "Hiring Co"
    assert team["is_owner"] is True
    assert len(team["invite_code"]) == 8
    assert [m["full_name"] for m in team["members"]] == ["Recruiter One"]


def test_recruiter_without_a_company_sees_an_empty_team(client, recruiter):
    team = client.get("/recruiter/team", headers=recruiter["headers"]).json()
    assert team["company_name"] is None
    assert team["members"] == []


def test_joining_with_the_code_works(client, recruiter, recruiter2):
    make_team(client, recruiter, recruiter2)
    team = client.get("/recruiter/team", headers=recruiter2["headers"]).json()
    assert team["company_name"] == "Hiring Co"
    assert team["is_owner"] is False
    assert team["invite_code"] is None
    assert len(team["members"]) == 2


def test_code_works_in_lowercase_with_a_dash(client, recruiter, recruiter2):
    company(client, recruiter["headers"])
    code = client.get("/recruiter/team", headers=recruiter["headers"]).json()["invite_code"]
    typed = f"{code[:4]}-{code[4:]}".lower()
    response = client.post("/recruiter/team/join", json={"code": typed}, headers=recruiter2["headers"])
    assert response.status_code == 200


def test_wrong_code_is_refused(client, recruiter, recruiter2):
    company(client, recruiter["headers"])
    response = client.post("/recruiter/team/join", json={"code": "ZZZZZZZZ"}, headers=recruiter2["headers"])
    assert response.status_code == 400


def test_someone_with_a_company_cannot_join_another(client, recruiter, recruiter2):
    company(client, recruiter["headers"])
    company(client, recruiter2["headers"], name="Other Co")
    code = client.get("/recruiter/team", headers=recruiter["headers"]).json()["invite_code"]
    response = client.post("/recruiter/team/join", json={"code": code}, headers=recruiter2["headers"])
    assert response.status_code == 400


def test_job_seekers_cannot_join_a_team(client, recruiter, seeker):
    company(client, recruiter["headers"])
    code = client.get("/recruiter/team", headers=recruiter["headers"]).json()["invite_code"]
    response = client.post("/recruiter/team/join", json={"code": code}, headers=seeker["headers"])
    assert response.status_code == 403


def test_team_members_share_jobs_and_applicants(client, recruiter, recruiter2, seeker, make_resume):
    make_team(client, recruiter, recruiter2)
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    assert [j["id"] for j in client.get("/recruiter/jobs", headers=recruiter2["headers"]).json()] == [job_id]

    edited = client.patch(
        f"/recruiter/jobs/{job_id}", json=job_payload(title="Edited by member"), headers=recruiter2["headers"]
    )
    assert edited.status_code == 200

    apply(client, seeker, job_id, make_resume)
    applicants = client.get(f"/recruiter/jobs/{job_id}/applicants", headers=recruiter2["headers"]).json()
    changed = client.patch(
        f"/recruiter/applications/{applicants[0]['application_id']}/status",
        json={"status": "shortlisted"},
        headers=recruiter2["headers"],
    )
    assert changed.status_code == 200


def test_member_cannot_edit_the_company_profile(client, recruiter, recruiter2):
    make_team(client, recruiter, recruiter2)
    response = client.put(
        "/recruiter/company", json={"name": "Renamed By Member", "company_type": "startup"}, headers=recruiter2["headers"]
    )
    assert response.status_code == 403


def test_member_cannot_make_a_new_code_or_remove_people(client, recruiter, recruiter2):
    make_team(client, recruiter, recruiter2)
    assert client.post("/recruiter/team/regenerate", headers=recruiter2["headers"]).status_code == 403
    owner_id = recruiter["user"]["id"]
    assert client.delete(f"/recruiter/team/members/{owner_id}", headers=recruiter2["headers"]).status_code == 403


def test_new_code_stops_the_old_one(client, recruiter, recruiter2):
    company(client, recruiter["headers"])
    old = client.get("/recruiter/team", headers=recruiter["headers"]).json()["invite_code"]
    new = client.post("/recruiter/team/regenerate", headers=recruiter["headers"]).json()["invite_code"]
    assert new != old
    assert client.post("/recruiter/team/join", json={"code": old}, headers=recruiter2["headers"]).status_code == 400
    assert client.post("/recruiter/team/join", json={"code": new}, headers=recruiter2["headers"]).status_code == 200


def test_owner_can_remove_a_member_who_then_loses_access(client, recruiter, recruiter2):
    make_team(client, recruiter, recruiter2)
    post_job(client, recruiter["headers"])
    response = client.delete(f"/recruiter/team/members/{recruiter2['user']['id']}", headers=recruiter["headers"])
    assert response.status_code == 200
    assert len(response.json()["members"]) == 1
    assert client.get("/recruiter/team", headers=recruiter2["headers"]).json()["company_name"] is None
    assert client.get("/recruiter/jobs", headers=recruiter2["headers"]).json() == []


def test_owner_cannot_remove_themselves(client, recruiter):
    company(client, recruiter["headers"])
    response = client.delete(f"/recruiter/team/members/{recruiter['user']['id']}", headers=recruiter["headers"])
    assert response.status_code == 400


def test_owner_cannot_leave_but_a_member_can(client, recruiter, recruiter2):
    make_team(client, recruiter, recruiter2)
    assert client.post("/recruiter/team/leave", headers=recruiter["headers"]).status_code == 400
    assert client.post("/recruiter/team/leave", headers=recruiter2["headers"]).status_code == 200
    assert client.get("/recruiter/team", headers=recruiter2["headers"]).json()["company_name"] is None

def test_too_many_wrong_codes_are_blocked(client, recruiter, recruiter2):
    company(client, recruiter["headers"])
    for _ in range(10):
        response = client.post(
            "/recruiter/team/join", json={"code": "ZZZZZZZZ"}, headers=recruiter2["headers"]
        )
        assert response.status_code == 400
    blocked = client.post("/recruiter/team/join", json={"code": "ZZZZZZZZ"}, headers=recruiter2["headers"])
    assert blocked.status_code == 429