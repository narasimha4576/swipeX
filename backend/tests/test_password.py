import re

from sqlalchemy import func, select

from app.models import RecoveryCode
from tests.conftest import PASSWORD

NEW = "Brand-new-pass-9"
WRONG = "Wrong-password-1"
EMAIL = "seeker@example.com"
CODE_FORMAT = re.compile(r"^[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$")


def change(client, headers, current=PASSWORD, new=NEW):
    return client.post(
        "/auth/change-password", json={"current_password": current, "new_password": new}, headers=headers
    )


def make_codes(client, headers, password=None):
    response = client.post("/auth/recovery", json={"password": password}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["codes"]


def forgot(client, email, code, password=NEW):
    return client.post("/auth/forgot", json={"email": email, "recovery_code": code, "new_password": password})


def login_status(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password}).status_code


# ---------- changing the password ----------


def test_change_password_needs_a_login(client):
    response = client.post("/auth/change-password", json={"current_password": PASSWORD, "new_password": NEW})
    assert response.status_code == 401


def test_changing_the_password_works(client, seeker):
    assert change(client, seeker["headers"]).status_code == 204
    assert login_status(client, EMAIL, NEW) == 200
    assert login_status(client, EMAIL, PASSWORD) == 401


def test_a_wrong_current_password_changes_nothing(client, seeker):
    assert change(client, seeker["headers"], current=WRONG).status_code == 400
    assert login_status(client, EMAIL, PASSWORD) == 200


def test_the_new_password_must_be_long_enough_and_different(client, seeker):
    assert change(client, seeker["headers"], new="short").status_code == 422
    assert change(client, seeker["headers"], new=PASSWORD).status_code == 400


def test_wrong_current_passwords_are_limited(client, seeker):
    for _ in range(5):
        assert change(client, seeker["headers"], current=WRONG).status_code == 400
    assert change(client, seeker["headers"]).status_code == 429


def test_changing_the_password_leaves_a_notice(client, seeker):
    change(client, seeker["headers"])
    items = client.get("/notifications", headers=seeker["headers"]).json()["items"]
    assert any(n["title"] == "Your password was changed" for n in items)


# ---------- recovery codes ----------


def test_recovery_codes_start_empty(client, seeker):
    assert client.get("/auth/recovery", headers=seeker["headers"]).json() == {"created": False, "remaining": 0}


def test_the_first_codes_need_no_password(client, seeker):
    codes = make_codes(client, seeker["headers"])
    assert len(codes) == 8 and len(set(codes)) == 8
    assert all(CODE_FORMAT.match(code) for code in codes)
    assert client.get("/auth/recovery", headers=seeker["headers"]).json() == {"created": True, "remaining": 8}


def test_codes_are_not_stored_as_text(client, db, seeker):
    codes = make_codes(client, seeker["headers"])
    stored = db.scalars(select(RecoveryCode.code_hash)).all()
    assert len(stored) == 8
    assert all(len(value) == 64 for value in stored)
    for code in codes:
        assert code not in stored and code.replace("-", "") not in stored


def test_new_codes_need_the_password_and_replace_the_old_ones(client, seeker):
    old = make_codes(client, seeker["headers"])
    assert client.post("/auth/recovery", json={}, headers=seeker["headers"]).status_code == 400
    assert client.post("/auth/recovery", json={"password": WRONG}, headers=seeker["headers"]).status_code == 400
    new = make_codes(client, seeker["headers"], password=PASSWORD)
    assert forgot(client, EMAIL, old[0]).status_code == 400
    assert forgot(client, EMAIL, new[0]).status_code == 204


# ---------- forgot password ----------


def test_forgot_password_with_a_code(client, seeker):
    codes = make_codes(client, seeker["headers"])
    assert forgot(client, EMAIL, codes[0]).status_code == 204
    assert login_status(client, EMAIL, NEW) == 200
    assert login_status(client, EMAIL, PASSWORD) == 401
    assert client.get("/auth/recovery", headers=seeker["headers"]).json()["remaining"] == 7


def test_a_code_works_only_once(client, seeker):
    codes = make_codes(client, seeker["headers"])
    assert forgot(client, EMAIL, codes[0]).status_code == 204
    assert forgot(client, EMAIL, codes[0], password="Another-pass-77").status_code == 400
    assert forgot(client, EMAIL, codes[1], password="Another-pass-77").status_code == 204


def test_codes_can_be_typed_loosely(client, seeker):
    code = make_codes(client, seeker["headers"])[0]
    loose = " " + code.replace("-", "").lower() + " "
    assert forgot(client, EMAIL.upper(), loose).status_code == 204


def test_a_wrong_email_and_a_wrong_code_get_the_same_answer(client, seeker):
    code = make_codes(client, seeker["headers"])[0]
    wrong_code = forgot(client, EMAIL, "AAAA-BBBB-CCCC")
    wrong_email = forgot(client, "nobody@example.com", code)
    assert wrong_code.status_code == wrong_email.status_code == 400
    assert wrong_code.json()["detail"] == wrong_email.json()["detail"]


def test_someone_elses_code_does_not_work(client, seeker, seeker2):
    code = make_codes(client, seeker["headers"])[0]
    assert forgot(client, "seeker2@example.com", code).status_code == 400


def test_guessing_codes_is_limited(client, seeker):
    code = make_codes(client, seeker["headers"])[0]
    for _ in range(5):
        assert forgot(client, EMAIL, "AAAA-BBBB-CCCC").status_code == 400
    assert forgot(client, EMAIL, code).status_code == 429


def test_a_disabled_account_cannot_reset(client, seeker, disable_user):
    code = make_codes(client, seeker["headers"])[0]
    disable_user(EMAIL)
    assert forgot(client, EMAIL, code).status_code == 400


def test_a_too_short_new_password_does_not_use_up_the_code(client, seeker):
    code = make_codes(client, seeker["headers"])[0]
    assert forgot(client, EMAIL, code, password="short").status_code == 422
    assert forgot(client, EMAIL, code).status_code == 204


def test_a_reset_leaves_a_notice(client, seeker):
    code = make_codes(client, seeker["headers"])[0]
    forgot(client, EMAIL, code)
    items = client.get("/notifications", headers=seeker["headers"]).json()["items"]
    assert any(n["title"] == "Your password was changed" for n in items)


def test_the_admin_can_use_the_same_tools(client, admin):
    codes = make_codes(client, admin["headers"])
    assert forgot(client, "admin@example.com", codes[0]).status_code == 204
    assert login_status(client, "admin@example.com", NEW) == 200


def test_deleting_the_account_removes_the_codes(client, db, seeker):
    make_codes(client, seeker["headers"])
    response = client.post(
        "/account/delete", json={"password": PASSWORD, "confirm": "DELETE"}, headers=seeker["headers"]
    )
    assert response.status_code == 204
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(RecoveryCode)) == 0