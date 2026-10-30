import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        if payload.get("scope"):
            raise credentials_error
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise credentials_error

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_roles(*roles: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to do this",
            )
        return current_user

    return checker


def get_autofill_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = decode_access_token(token)
        if payload.get("scope") != "autofill":
            raise error
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise error
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.role != "job_seeker":
        raise error
    return user