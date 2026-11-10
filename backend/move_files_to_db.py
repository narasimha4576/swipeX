"""Copies resume and photo files from the disk into the database. Safe to run many times.
Run it with:   python backend/move_files_to_db.py
"""
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Profile, Resume
from app.routers import profile_extras, resumes


def main():
    moved_resumes = moved_photos = missing = 0
    with SessionLocal() as db:
        for resume in db.scalars(select(Resume).where(Resume.file_data.is_(None))):
            path = resumes.UPLOAD_DIR / resume.file_path
            if path.is_file():
                resume.file_data = path.read_bytes()
                moved_resumes += 1
            else:
                missing += 1
        for profile in db.scalars(
            select(Profile).where(Profile.photo_path.is_not(None), Profile.photo_data.is_(None))
        ):
            path = profile_extras.PHOTO_DIR / profile.photo_path
            if path.is_file():
                profile.photo_data = path.read_bytes()
                moved_photos += 1
            else:
                missing += 1
        db.commit()
    print(f"Moved {moved_resumes} resume(s) and {moved_photos} photo(s) into the database. Files not found: {missing}.")


if __name__ == "__main__":
    main()