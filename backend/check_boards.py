import json
import sys
import time

import httpx

from app.importers import ashby, greenhouse, lever
from app.importers.sync import BOARDS_FILE, SOURCES, load_boards

CANDIDATES = {
    "greenhouse": [
        "stripe", "airbnb", "databricks", "cloudflare", "coinbase", "reddit", "discord",
        "figma", "dropbox", "pinterest", "twilio", "asana", "mongodb", "elastic", "okta",
        "datadog", "gitlab", "lyft", "instacart", "duolingo", "grammarly", "robinhood",
        "razorpay", "postman", "browserstack", "groww", "phonepe", "cred", "zeta",
        "freshworks", "swiggy", "meesho", "unacademy",
    ],
    "lever": ["palantir", "matchgroup", "unlimit", "leverdemo", "plaid", "gopuff", "spotify"],
    "ashby": [
        "openai", "ramp", "notion", "linear", "vanta", "replit", "cursor", "snowflake",
        "harvey", "perplexity", "fal-ai",
    ],
}


def main() -> None:
    args = [a.lower() if a.lower() in SOURCES else a for a in sys.argv[1:]]
    if args and args[0] in SOURCES:
        plan = [(SOURCES[args[0]], args[1:] or CANDIDATES[args[0]])]
    elif args:
        plan = [(SOURCES["greenhouse"], args)]
    else:
        plan = [(SOURCES[name], CANDIDATES[name]) for name in ("greenhouse", "lever", "ashby")]

    existing = {(b["source"], b["token"]): b for b in load_boards()}
    print(f"{'source':<12}{'board':<18}{'company':<24}{'jobs':>6}{'matching':>10}")

    with httpx.Client(
        timeout=30, headers=greenhouse.HEADERS, follow_redirects=True
    ) as client:
        for module, tokens in plan:
            for token in tokens:
                try:
                    jobs = module.fetch_jobs(token, client)
                except Exception:
                    print(f"{module.SOURCE:<12}{token:<18}not found")
                    time.sleep(0.4)
                    continue

                name = module.fetch_board_name(token, client) or token
                matching = [raw for raw in jobs if module.to_job_fields(raw) is not None]
                print(f"{module.SOURCE:<12}{token:<18}{name[:22]:<24}{len(jobs):>6}{len(matching):>10}")

                key = (module.SOURCE, token)
                if matching and key not in existing:
                    existing[key] = {
                        "source": module.SOURCE,
                        "token": token,
                        "name": name,
                        "company_type": "mnc" if len(jobs) >= 150 else "startup",
                    }
                time.sleep(0.5)

    BOARDS_FILE.write_text(json.dumps(list(existing.values()), indent=2), encoding="utf-8")
    print(f"\nSaved {len(existing)} company boards to {BOARDS_FILE.name}")


if __name__ == "__main__":
    main()