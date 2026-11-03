from app.notifications import check_saved_searches


def save(client, headers, name="Python jobs", filters=None):
    return client.post(
        "/saved-searches",
        json={"name": name, "filters": filters if filters is not None else {"q": "python"}},
        headers=headers,
    )


def unread(client, headers):
    return client.get("/notifications/unread-count", headers=headers).json()["unread"]


def test_save_and_list_a_search(client, seeker):
    response = save(client, seeker["headers"])
    assert response.status_code == 200, response.text
    listed = client.get("/saved-searches", headers=seeker["headers"]).json()
    assert [s["name"] for s in listed] == ["Python jobs"]
    assert listed[0]["filters"]["q"] == "python"


def test_a_search_without_a_name_gets_one(client, seeker):
    response = save(client, seeker["headers"], name=None, filters={"q": "python", "remote": True})
    assert response.status_code == 200
    assert "python" in response.json()["name"].lower()


def test_empty_search_is_refused(client, seeker):
    assert save(client, seeker["headers"], filters={}).status_code == 400


def test_limit_is_ten_searches(client, seeker):
    for i in range(10):
        assert save(client, seeker["headers"], name=f"Search {i}").status_code == 200
    assert save(client, seeker["headers"], name="Too many").status_code == 400


def test_delete_own_search_but_not_someone_elses(client, seeker, seeker2):
    created = save(client, seeker["headers"]).json()
    assert client.delete(f"/saved-searches/{created['id']}", headers=seeker2["headers"]).status_code == 404
    assert client.delete(f"/saved-searches/{created['id']}", headers=seeker["headers"]).status_code == 200
    assert client.get("/saved-searches", headers=seeker["headers"]).json() == []


def test_recruiters_cannot_save_searches(client, recruiter):
    assert save(client, recruiter["headers"]).status_code == 403


def test_matching_new_job_creates_one_notification(client, seeker, make_job):
    created = save(client, seeker["headers"]).json()
    make_job("Python Engineer")
    make_job("Head Chef", skills=["Cooking"])
    assert check_saved_searches() == 1

    data = client.get("/notifications", headers=seeker["headers"]).json()
    assert data["unread"] == 1
    assert data["items"][0]["title"] == "1 new job for Python jobs"
    assert data["items"][0]["link"] == f"/jobs?search={created['id']}"


def test_jobs_that_do_not_match_do_not_notify(client, seeker, make_job):
    save(client, seeker["headers"])
    make_job("Head Chef", skills=["Cooking"])
    assert check_saved_searches() == 0
    assert unread(client, seeker["headers"]) == 0


def test_checking_twice_does_not_repeat_the_alert(client, seeker, make_job):
    save(client, seeker["headers"])
    make_job("Python Engineer")
    assert check_saved_searches() == 1
    assert check_saved_searches() == 0
    assert len(client.get("/notifications", headers=seeker["headers"]).json()["items"]) == 1


def test_unread_alerts_are_merged_into_one(client, seeker, make_job):
    save(client, seeker["headers"])
    make_job("Python Engineer")
    check_saved_searches()
    make_job("Python Developer", company="Beta Corp")
    check_saved_searches()
    items = client.get("/notifications", headers=seeker["headers"]).json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "2 new jobs for Python jobs"


def test_after_reading_a_new_match_makes_a_new_alert(client, seeker, make_job):
    save(client, seeker["headers"])
    make_job("Python Engineer")
    check_saved_searches()
    first = client.get("/notifications", headers=seeker["headers"]).json()["items"][0]["id"]
    client.post(f"/notifications/{first}/read", headers=seeker["headers"])
    assert unread(client, seeker["headers"]) == 0
    make_job("Python Developer", company="Beta Corp")
    check_saved_searches()
    assert len(client.get("/notifications", headers=seeker["headers"]).json()["items"]) == 2
    assert unread(client, seeker["headers"]) == 1


def test_mark_all_read(client, seeker, make_job):
    save(client, seeker["headers"], name="One")
    save(client, seeker["headers"], name="Two", filters={"skill": "Cooking"})
    make_job("Python Engineer")
    make_job("Head Chef", skills=["Cooking"])
    check_saved_searches()
    assert unread(client, seeker["headers"]) == 2
    client.post("/notifications/read-all", headers=seeker["headers"])
    assert unread(client, seeker["headers"]) == 0


def test_notifications_are_private(client, seeker, seeker2, make_job):
    save(client, seeker["headers"])
    make_job("Python Engineer")
    check_saved_searches()
    assert client.get("/notifications", headers=seeker2["headers"]).json()["items"] == []
    note_id = client.get("/notifications", headers=seeker["headers"]).json()["items"][0]["id"]
    client.post(f"/notifications/{note_id}/read", headers=seeker2["headers"])
    assert unread(client, seeker["headers"]) == 1


def test_notifications_need_a_login(client):
    assert client.get("/notifications").status_code == 401
    assert client.get("/notifications/unread-count").status_code == 401