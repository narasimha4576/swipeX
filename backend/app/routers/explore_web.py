import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import news, web_search
from app.ai import is_configured
from app.deps import get_current_user, get_db
from app.importers import lookup
from app.models import Company, User
from app.routers.explore import jobs_for, run_summary
from app.schemas import NewsItem, SummaryOut, VideoItem, WebJob, WebOverview, WebResult

router = APIRouter(prefix="/explore", tags=["explore"])
CACHE_SECONDS = 1200
_cache: dict[str, tuple[float, dict]] = {}


def gather(name: str) -> dict:
    key = name.lower()
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]

    data: dict = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            "jobs": pool.submit(lookup.find_jobs, name),
            "news": pool.submit(news.recent_news, name),
            "web": pool.submit(web_search.web_and_images, f"{name} company"),
            "videos": pool.submit(web_search.videos, f"{name} company"),
        }
        for label, future in futures.items():
            try:
                data[label] = future.result(timeout=45)
            except Exception:
                data[label] = {"results": [], "images": []} if label == "web" else []
    _cache[key] = (time.time(), data)
    return data


def match_company(db: Session, name: str):
    return db.scalar(
        select(Company).where(
            func.lower(Company.name) == name.lower(),
            Company.verification_status != "rejected",
        )
    )


@router.get("/web", response_model=WebOverview)
def web_overview(
    name: str = Query(..., min_length=2, max_length=80),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    text = name.strip()
    match = match_company(db, text)
    data = gather(text)
    return WebOverview(
        name=text,
        swipex_company_id=match.id if match else None,
        swipex_jobs=jobs_for(db, match.id) if match else [],
        live_jobs=[WebJob(**job) for job in data["jobs"]],
        news=[NewsItem(**item) for item in data["news"]],
        results=[WebResult(**item) for item in data["web"]["results"]],
        images=data["web"]["images"],
        videos=[VideoItem(**item) for item in data["videos"]],
        videos_enabled=web_search.videos_enabled(),
        ai_available=is_configured(),
    )


@router.post("/web/summary", response_model=SummaryOut)
def web_summary(
    name: str = Query(..., min_length=2, max_length=80),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    text = name.strip()
    data = gather(text)
    snippets = " ".join(item["snippet"] for item in data["web"]["results"][:4])[:700]
    titles = [job["title"] for job in data["jobs"][:10]]
    return run_summary(f"web:{text.lower()}", text, {"description": snippets}, data["news"], titles)