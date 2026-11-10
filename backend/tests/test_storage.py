from sqlalchemy import select

import app.routers.profile_extras as extras
import app.routers.resumes as resumes_module
from app.models import Profile, Resume
from move_files_to_db import main as move_files
from tests.test_profile_extras import png_bytes
from tests.test_security import make_pdf, upload


def legacy_resume(db, user_id, name="legacy.pdf", content=None):
    if content is not None:
        (resumes_module.UPLOAD_DIR / name).write_bytes(content)
    resume = Resume(user_id=user_id, version_name="Old", file_path=name, is_default=True)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def test_a_new_resume_lives_in_the_database_not_on_the_disk(client, db, seeker):
    pdf = make_pdf()
    assert upload(client, seeker["headers"], pdf).status_code == 201
    resume = db.scalar(select(Resume))
    assert bytes(resume.file_data) == pdf
    assert not list(resumes_module.UPLOAD_DIR.glob("*.pdf"))
    download = client.get(f"/resumes/{resume.id}/file", headers=seeker["headers"])
    assert download.status_code == 200
    assert download.content == pdf
    assert download.headers["content-type"] == "application/pdf"


def test_an_old_resume_on_the_disk_still_downloads(client, db, seeker):
    pdf = make_pdf()
    resume = legacy_resume(db, seeker["user"]["id"], content=pdf)
    assert client.get(f"/resumes/{resume.id}/file", headers=seeker["headers"]).content == pdf


def test_a_resume_with_no_file_anywhere_gives_a_clean_404(client, db, seeker):
    resume = legacy_resume(db, seeker["user"]["id"], name="gone.pdf")
    assert client.get(f"/resumes/{resume.id}/file", headers=seeker["headers"]).status_code == 404


def test_the_analysis_works_from_the_database_copy(client, seeker):
    resume_id = upload(client, seeker["headers"], make_pdf()).json()["id"]
    assert client.get(f"/resumes/{resume_id}/analysis", headers=seeker["headers"]).status_code == 200


def test_a_new_photo_lives_in_the_database(client, db, seeker):
    url = client.post(
        "/profile/photo", files={"file": ("me.png", png_bytes(), "image/png")}, headers=seeker["headers"]
    ).json()["photo_url"]
    db.expire_all()
    profile = db.scalar(select(Profile))
    assert profile.photo_data and len(bytes(profile.photo_data)) > 100
    assert not list(extras.PHOTO_DIR.glob("*.jpg"))
    served = client.get(url)
    assert served.status_code == 200 and served.headers["content-type"] == "image/jpeg"


def test_removing_the_photo_clears_the_database_copy(client, db, seeker):
    url = client.post(
        "/profile/photo", files={"file": ("me.png", png_bytes(), "image/png")}, headers=seeker["headers"]
    ).json()["photo_url"]
    client.delete("/profile/photo", headers=seeker["headers"])
    db.expire_all()
    assert db.scalar(select(Profile)).photo_data is None
    assert client.get(url).status_code == 404


def test_an_old_photo_on_the_disk_still_shows(client, db, seeker):
    client.put("/profile/me", json={"headline": "x"}, headers=seeker["headers"])
    name = "u1-0123456789abcdef.jpg"
    (extras.PHOTO_DIR / name).write_bytes(b"old-photo-bytes")
    profile = db.scalar(select(Profile))
    profile.photo_path = name
    db.commit()
    assert client.get(f"/photos/{name}").content == b"old-photo-bytes"


def test_the_move_script_copies_disk_files_into_the_database(client, db, seeker):
    pdf = make_pdf()
    resume = legacy_resume(db, seeker["user"]["id"], content=pdf)
    client.put("/profile/me", json={"headline": "x"}, headers=seeker["headers"])
    name = "u1-0123456789abcdef.jpg"
    (extras.PHOTO_DIR / name).write_bytes(b"old-photo-bytes")
    profile = db.scalar(select(Profile))
    profile.photo_path = name
    db.commit()

    move_files()
    move_files()  # running it twice is harmless

    db.expire_all()
    assert bytes(db.get(Resume, resume.id).file_data) == pdf
    assert bytes(db.scalar(select(Profile)).photo_data) == b"old-photo-bytes"