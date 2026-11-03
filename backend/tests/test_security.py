import io
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.security_setup import check_secret_key, install_security
from tests.conftest import PASSWORD
from tests.test_profile_extras import png_bytes
from tests.test_recruiter import company, post_job

WRONG = "Wrong-password-1"


def bad_login(client, email):
    return client.post("/auth/login", data={"username": email, "password": WRONG})


def good_login(client, email):
    return client.post("/auth/login", data={"username": email, "password": PASSWORD})


def make_pdf(pages=1, password=None):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    if password:
        writer.encrypt(password)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def upload(client, headers, content, name="Main"):
    return client.post(
        "/resumes", data={"version_name": name}, files={"file": ("cv.pdf", content, "application/pdf")}, headers=headers
    )


# ---------- login and sign-up limits ----------


def test_login_is_blocked_after_five_wrong_passwords(client, register):
    register("victim@example.com")
    for _ in range(5):
        assert bad_login(client, "victim@example.com").status_code == 401
    blocked = good_login(client, "victim@example.com")
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_guessing_unknown_emails_is_blocked_too(client):
    for _ in range(5):
        assert bad_login(client, "ghost@example.com").status_code == 401
    assert bad_login(client, "ghost@example.com").status_code == 429


def test_a_good_login_resets_the_counter(client, register):
    register("reset@example.com")
    for _ in range(4):
        assert bad_login(client, "reset@example.com").status_code == 401
    assert good_login(client, "reset@example.com").status_code == 200
    for _ in range(4):
        assert bad_login(client, "reset@example.com").status_code == 401
    assert good_login(client, "reset@example.com").status_code == 200


def test_blocking_one_account_does_not_block_another(client, register):
    register("victim2@example.com")
    register("friend@example.com")
    for _ in range(5):
        bad_login(client, "victim2@example.com")
    assert bad_login(client, "victim2@example.com").status_code == 429
    assert good_login(client, "friend@example.com").status_code == 200


def test_one_network_cannot_try_too_many_accounts(client, register):
    register("real@example.com")
    for i in range(30):
        assert bad_login(client, f"nobody{i}@example.com").status_code == 401
    assert good_login(client, "real@example.com").status_code == 429


def test_too_many_registrations_from_one_network_are_blocked(client):
    def create(i):
        return client.post(
            "/auth/register",
            json={"email": f"bulk{i}@example.com", "password": PASSWORD, "full_name": "Bulk", "role": "job_seeker"},
        )

    for i in range(10):
        assert create(i).status_code == 201
    assert create(10).status_code == 429


# ---------- tokens ----------


def forged(key, algorithm, user_id=1, role="admin"):
    payload = {"sub": str(user_id), "role": role, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return {"Authorization": "Bearer " + jwt.encode(payload, key, algorithm=algorithm)}


def test_autofill_token_cannot_open_normal_pages(client, seeker):
    token = client.post("/autofill/token", headers=seeker["headers"]).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert client.get("/profile/me", headers=headers).status_code == 401


def test_old_token_stops_working_when_the_account_is_disabled(client, seeker, admin):
    assert client.get("/auth/me", headers=seeker["headers"]).status_code == 200
    client.patch(
        f"/admin/users/{seeker['user']['id']}/active", params={"is_active": "false"}, headers=admin["headers"]
    )
    assert client.get("/auth/me", headers=seeker["headers"]).status_code == 401


def test_a_changed_token_is_refused(client, seeker):
    token = seeker["headers"]["Authorization"].split()[1]
    head, body, signature = token.split(".")
    body = body[:-2] + ("AA" if not body.endswith("AA") else "BB")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {head}.{body}.{signature}"})
    assert response.status_code == 401


def test_a_token_signed_with_another_key_is_refused(client, admin):
    headers = forged("x" * 48, "HS256", user_id=admin["user"]["id"])
    assert client.get("/admin/users", headers=headers).status_code == 401


def test_a_token_with_no_signature_is_refused(client, admin):
    headers = forged(None, "none", user_id=admin["user"]["id"])
    assert client.get("/admin/users", headers=headers).status_code == 401


# ---------- nobody sees anybody else's data ----------


def test_other_users_resume_file_is_private(client, seeker, seeker2):
    resume_id = upload(client, seeker["headers"], make_pdf()).json()["id"]
    assert client.get(f"/resumes/{resume_id}/file", headers=seeker["headers"]).status_code == 200
    assert client.get(f"/resumes/{resume_id}/file", headers=seeker2["headers"]).status_code == 404


def test_cannot_delete_or_change_someone_elses_resume(client, seeker, seeker2):
    resume_id = upload(client, seeker["headers"], make_pdf()).json()["id"]
    assert client.delete(f"/resumes/{resume_id}", headers=seeker2["headers"]).status_code == 404
    assert client.patch(f"/resumes/{resume_id}/default", headers=seeker2["headers"]).status_code == 404


def test_cannot_remove_someone_elses_saved_job(client, seeker, seeker2, make_job):
    job = make_job()
    client.post("/swipes", json={"job_id": job.id, "direction": "right"}, headers=seeker["headers"])
    application_id = client.get("/applications", headers=seeker["headers"]).json()[0]["id"]
    assert client.delete(f"/applications/{application_id}", headers=seeker2["headers"]).status_code == 404


def test_autofill_refuses_someone_elses_resume(client, seeker, seeker2, make_job):
    job = make_job()
    resume_id = upload(client, seeker["headers"], make_pdf()).json()["id"]
    response = client.get(
        f"/autofill/payload/{job.id}",
        params={"include_resume": "true", "resume_id": resume_id},
        headers=seeker2["headers"],
    )
    assert response.status_code in (400, 403, 404)


def test_recruiters_only_open_resumes_of_their_own_applicants(client, recruiter, recruiter2, seeker):
    company(client, recruiter["headers"])
    company(client, recruiter2["headers"], name="Other Co")
    job_id = post_job(client, recruiter["headers"]).json()["id"]
    resume_id = upload(client, seeker["headers"], make_pdf()).json()["id"]
    client.post(
        "/applications/apply", json={"job_id": job_id, "resume_id": resume_id}, headers=seeker["headers"]
    )
    application_id = client.get(f"/recruiter/jobs/{job_id}/applicants", headers=recruiter["headers"]).json()[0][
        "application_id"
    ]
    url = f"/recruiter/applications/{application_id}/resume"
    own = client.get(url, headers=recruiter["headers"])
    assert own.status_code == 200
    assert own.headers["content-type"] == "application/pdf"
    assert client.get(url, headers=recruiter2["headers"]).status_code == 404
    assert client.get(url, headers=seeker["headers"]).status_code == 403


# ---------- uploads ----------


def test_a_normal_pdf_is_accepted(client, seeker):
    assert upload(client, seeker["headers"], make_pdf()).status_code == 201


def test_a_text_file_is_refused_as_a_resume(client, seeker):
    assert upload(client, seeker["headers"], b"just some text").status_code == 400


def test_a_fake_pdf_is_refused(client, seeker):
    response = upload(client, seeker["headers"], b"%PDF-1.4\nthis is not really a pdf")
    assert response.status_code == 400


def test_a_password_locked_pdf_is_refused(client, seeker):
    try:
        locked = make_pdf(password="secret123")
    except Exception:
        pytest.skip("This pypdf install cannot create locked PDFs")
    assert upload(client, seeker["headers"], locked).status_code == 400


def test_ten_pages_are_fine_but_eleven_are_too_long(client, seeker):
    assert upload(client, seeker["headers"], make_pdf(pages=10), name="Ten").status_code == 201
    assert upload(client, seeker["headers"], make_pdf(pages=11), name="Eleven").status_code == 400


def test_a_pdf_with_scripts_is_refused(client, seeker):
    risky = make_pdf() + b"\n% /JavaScript (app.alert(1))\n"
    assert upload(client, seeker["headers"], risky).status_code == 400


def test_a_resume_over_5mb_is_refused(client, seeker):
    assert upload(client, seeker["headers"], b"%PDF-" + b"0" * (5 * 1024 * 1024 + 1)).status_code == 400


def test_a_huge_request_is_refused_before_it_is_read(client, seeker):
    response = upload(client, seeker["headers"], b"%PDF-" + b"0" * (13 * 1024 * 1024))
    assert response.status_code == 413


# ---------- headers, websites allowed, settings ----------


def test_answers_carry_security_headers(client):
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"


def test_photos_can_still_be_cached(client, seeker):
    url = client.post(
        "/profile/photo", files={"file": ("me.png", png_bytes(), "image/png")}, headers=seeker["headers"]
    ).json()["photo_url"]
    assert "public" in client.get(url).headers["cache-control"]


def test_other_websites_are_not_allowed_by_cors(client):
    response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_the_frontend_is_allowed_by_cors(client):
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_a_short_secret_key_is_flagged():
    assert check_secret_key("short", production=False)
    assert check_secret_key("a" * 64, production=False) == []


def test_production_refuses_a_weak_secret_key():
    with pytest.raises(RuntimeError):
        check_secret_key("short", production=True)


def test_docs_are_hidden_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    small = FastAPI()
    install_security(small)
    assert TestClient(small).get("/docs").status_code == 404


def test_docs_are_open_while_developing(client):
    assert client.get("/docs").status_code == 200