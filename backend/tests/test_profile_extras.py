import io
import json

from PIL import Image


def png_bytes(size=(60, 40)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 80, 30)).save(buffer, "PNG")
    return buffer.getvalue()


def upload(client, headers, content, name="me.png", kind="image/png"):
    return client.post("/profile/photo", files={"file": (name, content, kind)}, headers=headers)


def test_photo_upload_and_download(client, seeker):
    response = upload(client, seeker["headers"], png_bytes())
    assert response.status_code == 200
    url = response.json()["photo_url"]
    assert url.startswith("/photos/")
    image = client.get(url)
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"
    client.delete("/profile/photo", headers=seeker["headers"])


def test_new_photo_replaces_the_old_one(client, seeker):
    first = upload(client, seeker["headers"], png_bytes()).json()["photo_url"]
    second = upload(client, seeker["headers"], png_bytes((80, 80))).json()["photo_url"]
    assert first != second
    assert client.get(first).status_code == 404
    assert client.get(second).status_code == 200
    client.delete("/profile/photo", headers=seeker["headers"])


def test_a_text_file_is_not_accepted_as_a_photo(client, seeker):
    assert upload(client, seeker["headers"], b"this is not an image").status_code == 400


def test_a_photo_over_3mb_is_refused(client, seeker):
    assert upload(client, seeker["headers"], b"0" * (3 * 1024 * 1024 + 1)).status_code == 400


def test_removing_the_photo_deletes_it(client, seeker):
    url = upload(client, seeker["headers"], png_bytes()).json()["photo_url"]
    response = client.delete("/profile/photo", headers=seeker["headers"])
    assert response.status_code == 200
    assert response.json()["photo_url"] is None
    assert client.get(url).status_code == 404


def test_public_profile_is_off_by_default(client, seeker):
    extras = client.get("/profile/extras", headers=seeker["headers"]).json()
    assert extras["is_public"] is False
    assert extras["slug"] is None


def test_public_profile_shows_safe_details_only(client, seeker):
    client.put(
        "/profile/me", json={"headline": "AI engineer", "skills": ["Python"]}, headers=seeker["headers"]
    )
    enabled = client.put("/profile/public", json={"enabled": True}, headers=seeker["headers"]).json()
    slug = enabled["slug"]
    assert slug

    response = client.get(f"/public/profiles/{slug}")  # no login
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Seeker One"
    assert data["headline"] == "AI engineer"
    assert "seeker@example.com" not in json.dumps(data)


def test_turning_public_profile_off_hides_it(client, seeker):
    slug = client.put("/profile/public", json={"enabled": True}, headers=seeker["headers"]).json()["slug"]
    client.put("/profile/public", json={"enabled": False}, headers=seeker["headers"])
    assert client.get(f"/public/profiles/{slug}").status_code == 404


def test_new_link_kills_the_old_link(client, seeker):
    old = client.put("/profile/public", json={"enabled": True}, headers=seeker["headers"]).json()["slug"]
    new = client.post("/profile/public/regenerate", headers=seeker["headers"]).json()["slug"]
    assert new != old
    assert client.get(f"/public/profiles/{old}").status_code == 404
    assert client.get(f"/public/profiles/{new}").status_code == 200


def test_disabled_user_public_profile_is_hidden(client, seeker, disable_user):
    slug = client.put("/profile/public", json={"enabled": True}, headers=seeker["headers"]).json()["slug"]
    disable_user("seeker@example.com")
    assert client.get(f"/public/profiles/{slug}").status_code == 404