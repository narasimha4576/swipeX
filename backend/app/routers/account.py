from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.account_data import DeletionBlocked, build_zip, delete_account
from app.deps import get_current_user, get_db
from app.models import User
from app.ratelimit import RateLimiter
from app.routers import profile_extras, resumes
from app.security import verify_password

router = APIRouter(prefix="/account", tags=["account"])

export_limit = RateLimiter(5, 3600, "You can download your data up to 5 times an hour. Please try again later.")
delete_limit = RateLimiter(5, 900, "Too many wrong passwords. Please wait a few minutes and try again.")


class DeleteIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)
    confirm: str = Field(max_length=50)


@router.get("/export")
def export_my_data(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    export_limit.hit(f"export:{user.id}")
    blob = build_zip(db, user, resumes.UPLOAD_DIR, profile_extras.PHOTO_DIR)
    return Response(
        content=blob,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="swipex-my-data.zip"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/delete", status_code=204)
def delete_my_account(
    data: DeleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Admin accounts cannot be deleted from the website.")
    key = f"delete:{user.id}"
    delete_limit.check(key)
    if data.confirm.strip().upper() != "DELETE":
        raise HTTPException(status_code=400, detail="Type DELETE to confirm")
    if not user.password_hash or not verify_password(data.password, user.password_hash):
        delete_limit.add(key)
        raise HTTPException(status_code=400, detail="That password is not correct")
    try:
        delete_account(db, user, resumes.UPLOAD_DIR, profile_extras.PHOTO_DIR)
    except DeletionBlocked as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return Response(status_code=204)