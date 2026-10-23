from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Experience, PortfolioItem, User
from app.schemas import (
    ExperienceCreate,
    ExperienceOut,
    PortfolioCreate,
    PortfolioOut,
)

router = APIRouter(prefix="/profile", tags=["profile"])

MAX_ITEMS = 20


def count_items(db: Session, model, user_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(model).where(model.user_id == user_id)
    )


# ---------- Experience ----------


@router.get("/experiences", response_model=list[ExperienceOut])
def list_experiences(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("job_seeker")),
):
    stmt = (
        select(Experience)
        .where(Experience.user_id == user.id)
        .order_by(Experience.start_year.desc(), Experience.id.desc())
    )
    return db.scalars(stmt).all()


@router.post(
    "/experiences", response_model=ExperienceOut, status_code=status.HTTP_201_CREATED
)
def add_experience(
    data: ExperienceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("job_seeker")),
):
    if count_items(db, Experience, user.id) >= MAX_ITEMS:
        raise HTTPException(
            status_code=400, detail=f"You can add up to {MAX_ITEMS} experiences"
        )
    item = Experience(user_id=user.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/experiences/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experience(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("job_seeker")),
):
    item = db.get(Experience, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Experience not found")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Portfolio ----------


@router.get("/portfolio", response_model=list[PortfolioOut])
def list_portfolio(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("job_seeker")),
):
    stmt = (
        select(PortfolioItem)
        .where(PortfolioItem.user_id == user.id)
        .order_by(PortfolioItem.id.desc())
    )
    return db.scalars(stmt).all()


@router.post(
    "/portfolio", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED
)
def add_portfolio_item(
    data: PortfolioCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("job_seeker")),
):
    if count_items(db, PortfolioItem, user.id) >= MAX_ITEMS:
        raise HTTPException(
            status_code=400, detail=f"You can add up to {MAX_ITEMS} portfolio links"
        )
    item = PortfolioItem(user_id=user.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/portfolio/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("job_seeker")),
):
    item = db.get(PortfolioItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)