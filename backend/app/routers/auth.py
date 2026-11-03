from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import User
from app.schemas import Token, UserCreate, UserOut
from fastapi import Request
from app.ratelimit import client_ip, login_by_account, login_by_ip, register_by_ip
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, request: Request, db: Session = Depends(get_db)):
    register_by_ip.hit(client_ip(request))
    email = data.email.lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


DUMMY_HASH = hash_password("swipex-timing-dummy")


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    ip = client_ip(request)
    email = form.username.strip().lower()
    account_key = f"{ip}|{email}"
    login_by_ip.check(ip)
    login_by_account.check(account_key)

    user = db.scalar(select(User).where(User.email == email))
    # Always check a password hash, even for unknown emails, so the timing gives nothing away.
    stored = user.password_hash if user and user.password_hash else DUMMY_HASH
    password_ok = verify_password(form.password, stored)
    if user is None or not user.password_hash or not password_ok:
        login_by_ip.add(ip)
        login_by_account.add(account_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    login_by_account.clear(account_key)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return Token(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user