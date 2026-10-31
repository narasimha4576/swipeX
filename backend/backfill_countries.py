from sqlalchemy import select

from app.database import SessionLocal
from app.geo import detect_country
from app.models import Job


def main() -> None:
    changed = 0
    with SessionLocal() as db:
        for job in db.scalars(select(Job)):
            country = detect_country(job.location)
            if country != job.country:
                job.country = country
                changed += 1
        db.commit()
    print(f"Updated the country on {changed} jobs")


if __name__ == "__main__":
    main()