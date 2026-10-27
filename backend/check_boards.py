import json
import sys
import time

import httpx

from app.importers import greenhouse
from app.importers.sync import BOARDS_FILE, load_boards

# Candidates to test. A board that does not exist is simply skipped.
CANDIDATES = [
    "stripe", "airbnb", "databricks", "cloudflare", "coinbase", "reddit", "discord",
    "figma", "dropbox", "pinterest", "twilio", "asana", "mongodb", "elastic", "okta",
    "datadog", "gitlab", "lyft", "instacart", "duolingo", "grammarly", "robinhood",
    "razorpay", "postman", "browserstack", "groww", "phonepe", "cred", "zeta",
    "freshworks", "swiggy", "meesho", "unacademy",
]


def main() -> None:
    tokens = [t.lower() for t in sys.argv[1:]] or CANDIDATES
    existing = {b["token"]: b for b in load_boards()}
    print(f"{'board':<16}{'company':<26}{'jobs':>6}{'matching':>10}")

    with httpx.Client(
        timeout=30, headers=greenhouse.HEADERS, follow_redirects=True
    ) as client:
        for token in tokens:
            try:
                jobs = greenhouse.fetch_jobs(token, client, with_content=False)
            except httpx.HTTPStatusError as exc:
                print(f"{token:<16}not found (HTTP {exc.response.status_code})")
                continue
            except Exception as exc:
                print(f"{token:<16}error: {exc}")
                continue

            name = greenhouse.fetch_board_name(token, client) or token
            matching = [
                j
                for j in jobs
                if greenhouse.is_relevant(
                    j.get("title") or "", (j.get("location") or {}).get("name") or ""
                )
            ]
            print(f"{token:<16}{name[:24]:<26}{len(jobs):>6}{len(matching):>10}")

            if matching and token not in existing:
                existing[token] = {
                    "token": token,
                    "name": name,
                    "company_type": "mnc" if len(jobs) >= 150 else "startup",
                }
            time.sleep(0.5)

    BOARDS_FILE.write_text(json.dumps(list(existing.values()), indent=2), encoding="utf-8")
    print(f"\nSaved {len(existing)} companies to {BOARDS_FILE.name}")


if __name__ == "__main__":
    main()