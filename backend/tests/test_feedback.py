from tests.conftest import PASSWORD


def send(client, headers=None, **extra):
    body = {"kind": "problem", "message": "The Jobs page does not load for me", "page": "/jobs"}
    body.update(extra)
    return client.post("/feedback", json=body, headers=headers or {})


def listing(client, admin, **params):
    response = client.get("/admin/feedback", params=params, headers=admin["headers"])
    assert response.status_code == 200, response.text
    return response.json()


def test_a_signed_out_person_can_report_a_problem(client, admin):
    assert send(client).status_code == 201
    item = listing(client, admin)["items"][0]
    assert item["kind"] == "problem" and item["status"] == "new" and item["page"] == "/jobs"
    assert item["who"] is None and item["signed_in"] is False


def test_bad_input_is_refused(client):
    assert send(client, message="no").status_code == 422
    assert send(client, message="x" * 2001).status_code == 422
    assert send(client, kind="rant").status_code == 422
    assert send(client, kind="feedback", rating=6).status_code == 422
    assert send(client, contact_email="not-an-email").status_code == 422


def test_a_rating_only_counts_for_feedback(client, admin):
    send(client, kind="problem", rating=4)
    assert listing(client, admin)["items"][0]["rating"] is None


def test_signed_in_feedback_is_anonymous_unless_allowed(client, admin, seeker):
    assert send(client, seeker["headers"], kind="feedback", message="I love the swipe cards", rating=5).status_code == 201
    data = listing(client, admin)
    item = data["items"][0]
    assert item["who"] is None and item["signed_in"] is True and item["rating"] == 5
    assert "seeker@example.com" not in str(data) and "Seeker One" not in str(data)


def test_allowing_contact_shows_the_name_and_email(client, admin, seeker):
    send(client, seeker["headers"], contact_ok=True)
    assert listing(client, admin)["items"][0]["who"] == {"name": "Seeker One", "email": "seeker@example.com"}


def test_a_signed_out_person_can_leave_an_email(client, admin):
    send(client, contact_email="reader@example.com")
    assert listing(client, admin)["items"][0]["who"] == {"name": None, "email": "reader@example.com"}


def test_signed_out_people_are_limited_to_five_an_hour(client):
    for _ in range(5):
        assert send(client).status_code == 201
    assert send(client).status_code == 429


def test_signed_in_people_are_limited_to_ten_an_hour(client, seeker):
    for _ in range(10):
        assert send(client, seeker["headers"]).status_code == 201
    assert send(client, seeker["headers"]).status_code == 429


def test_only_admins_read_or_change_feedback(client, seeker):
    feedback_id = send(client).json()["id"]
    assert client.get("/admin/feedback").status_code == 401
    responses = [
        client.get("/admin/feedback", headers=seeker["headers"]),
        client.patch(f"/admin/feedback/{feedback_id}", json={"status": "done"}, headers=seeker["headers"]),
        client.delete(f"/admin/feedback/{feedback_id}", headers=seeker["headers"]),
    ]
    assert [r.status_code for r in responses] == [403, 403, 403]


def test_filters_and_counts(client, admin):
    send(client)
    send(client, kind="feedback", message="Nice work on the app", rating=4)
    data = listing(client, admin)
    assert len(data["items"]) == 2 and data["counts"] == {"new": 2}
    assert [i["kind"] for i in listing(client, admin, kind="problem")["items"]] == ["problem"]
    assert listing(client, admin, status="done")["items"] == []


def test_the_admin_can_set_a_status_and_a_note(client, admin):
    feedback_id = send(client).json()["id"]
    response = client.patch(
        f"/admin/feedback/{feedback_id}",
        json={"status": "done", "note": "Fixed on Day 41"},
        headers=admin["headers"],
    )
    assert response.status_code == 200
    assert response.json()["status"] == "done" and response.json()["admin_note"] == "Fixed on Day 41"
    bad = client.patch(f"/admin/feedback/{feedback_id}", json={"status": "maybe"}, headers=admin["headers"])
    assert bad.status_code == 422
    assert listing(client, admin, status="done")["items"][0]["id"] == feedback_id


def test_the_admin_can_delete_and_it_is_logged(client, admin):
    feedback_id = send(client).json()["id"]
    assert client.delete(f"/admin/feedback/{feedback_id}", headers=admin["headers"]).status_code == 204
    assert listing(client, admin)["items"] == []
    log = client.get("/admin/overview", headers=admin["headers"]).json()["activity_log"]
    assert log[0]["action"] == "deleted_feedback"


def test_admins_get_a_bell_notification(client, admin, seeker):
    send(client)
    note = client.get("/notifications", headers=admin["headers"]).json()["items"][0]
    assert note["title"] == "New problem report" and note["link"] == "/admin/feedback"
    assert client.get("/notifications", headers=seeker["headers"]).json()["items"] == []
    send(client, kind="feedback", message="Great app, thanks")
    titles = [n["title"] for n in client.get("/notifications", headers=admin["headers"]).json()["items"]]
    assert "New feedback" in titles


def test_the_page_and_browser_are_cleaned(client, admin):
    send(client, headers={"User-Agent": "X" * 400}, page="/jobs/42?x=1")
    item = listing(client, admin)["items"][0]
    assert item["page"] == "/jobs/{id}"
    assert len(item["browser"]) == 160


def test_an_error_reference_is_kept_only_when_valid(client, admin):
    send(client, error_ref="3f9a1c2b")
    send(client, error_ref="not valid!")
    refs = {i["error_ref"] for i in listing(client, admin)["items"]}
    assert refs == {"3F9A1C2B", None}


def test_feedback_outlives_the_account_but_loses_the_name(client, admin, seeker):
    send(client, seeker["headers"], contact_ok=True)
    response = client.post(
        "/account/delete", json={"password": PASSWORD, "confirm": "DELETE"}, headers=seeker["headers"]
    )
    assert response.status_code == 204
    item = listing(client, admin)["items"][0]
    assert item["who"] is None and item["signed_in"] is False