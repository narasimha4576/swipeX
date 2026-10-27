import sys
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Company
from app.trust.service import enrich_company


def main() -> None:
    force = "--all" in sys.argv
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    with SessionLocal() as db:
        companies = db.scalars(
            select(Company).where(Company.verification_status == "verified").order_by(Company.id)
        ).all()
        print(f"{'company':<30}{'public record':<16}{'website':<10}{'domain age'}")
        for company in companies:
            if not force and company.enriched_at and company.enriched_at > cutoff:
                continue
            data = enrich_company(db, company)
            wiki = "yes" if data.get("wikidata") else "no"
            web = data.get("website") or {}
            site = "ok" if web.get("reachable") and web.get("https") else ("-" if not web else "problem")
            age = (data.get("domain") or {}).get("age_years")
            print(f"{company.name[:28]:<30}{wiki:<16}{site:<10}{age if age is not None else '-'}")
            time.sleep(1)


if __name__ == "__main__":
    main()