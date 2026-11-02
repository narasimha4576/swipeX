from sqlalchemy import select

from app.models import RecruiterProfile


def my_company_id(db, user):
    return (
        db.scalar(select(RecruiterProfile.company_id).where(RecruiterProfile.user_id == user.id))
        or -1
    )


def owner_user_id(db, company_id):
    return db.scalar(
        select(RecruiterProfile.user_id)
        .where(RecruiterProfile.company_id == company_id)
        .order_by(RecruiterProfile.id)
        .limit(1)
    )


def is_owner(db, user, company):
    return owner_user_id(db, company.id) == user.id