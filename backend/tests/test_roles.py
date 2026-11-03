def test_seeker_cannot_open_admin_area(client, seeker):
    assert client.get("/admin/users", headers=seeker["headers"]).status_code == 403


def test_seeker_cannot_open_recruiter_area(client, seeker):
    assert client.get("/recruiter/jobs", headers=seeker["headers"]).status_code == 403


def test_recruiter_cannot_open_seeker_profile(client, recruiter):
    assert client.get("/profile/me", headers=recruiter["headers"]).status_code == 403


def test_admin_cannot_open_seeker_profile(client, admin):
    assert client.get("/profile/me", headers=admin["headers"]).status_code == 403


def test_admin_area_needs_a_login(client):
    assert client.get("/admin/users").status_code == 401


def test_admin_can_list_users(client, admin, seeker):
    response = client.get("/admin/users", headers=admin["headers"])
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()]
    assert "seeker@example.com" in emails


def test_admin_can_disable_a_user_and_they_cannot_log_in(client, admin, seeker):
    user_id = seeker["user"]["id"]
    response = client.patch(
        f"/admin/users/{user_id}/active", params={"is_active": "false"}, headers=admin["headers"]
    )
    assert response.status_code == 200
    login = client.post("/auth/login", data={"username": "seeker@example.com", "password": "Passw0rd!123"})
    assert login.status_code == 403


def test_admin_cannot_disable_their_own_account(client, admin):
    response = client.patch(
        f"/admin/users/{admin['user']['id']}/active", params={"is_active": "false"}, headers=admin["headers"]
    )
    assert response.status_code == 400