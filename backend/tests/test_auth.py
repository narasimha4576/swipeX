from tests.conftest import PASSWORD


def test_register_returns_user_without_password(register):
    user = register("new@example.com", name="New Person")
    assert user["email"] == "new@example.com"
    assert user["role"] == "job_seeker"
    assert "password" not in user
    assert "password_hash" not in user


def test_register_recruiter(register):
    assert register("rec@example.com", role="recruiter")["role"] == "recruiter"


def test_register_duplicate_email_is_refused_even_with_different_case(client, register):
    register("dup@example.com")
    response = client.post(
        "/auth/register",
        json={"email": "DUP@example.com", "password": PASSWORD, "full_name": "Other", "role": "job_seeker"},
    )
    assert response.status_code == 400


def test_register_short_password_is_refused(client):
    response = client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": "short", "full_name": "A", "role": "job_seeker"},
    )
    assert response.status_code == 422


def test_register_bad_email_is_refused(client):
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": PASSWORD, "full_name": "A", "role": "job_seeker"},
    )
    assert response.status_code == 422


def test_nobody_can_register_as_admin(client):
    response = client.post(
        "/auth/register",
        json={"email": "boss@example.com", "password": PASSWORD, "full_name": "Boss", "role": "admin"},
    )
    assert response.status_code == 422


def test_login_gives_a_token(client, register):
    register("login@example.com")
    response = client.post("/auth/login", data={"username": "login@example.com", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_with_wrong_password_fails(client, register):
    register("wrong@example.com")
    response = client.post("/auth/login", data={"username": "wrong@example.com", "password": "Not-the-password-1"})
    assert response.status_code == 401


def test_login_with_unknown_email_fails(client):
    response = client.post("/auth/login", data={"username": "nobody@example.com", "password": PASSWORD})
    assert response.status_code == 401


def test_disabled_account_cannot_log_in(client, register, disable_user):
    register("off@example.com")
    disable_user("off@example.com")
    response = client.post("/auth/login", data={"username": "off@example.com", "password": PASSWORD})
    assert response.status_code == 403


def test_me_returns_the_logged_in_user(client, seeker):
    response = client.get("/auth/me", headers=seeker["headers"])
    assert response.status_code == 200
    assert response.json()["email"] == "seeker@example.com"


def test_me_without_token_is_refused(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_a_fake_token_is_refused(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer nonsense"})
    assert response.status_code == 401