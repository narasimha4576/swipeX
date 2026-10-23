import getpass
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password


def main():
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Admin password (min 8 characters): ")
    if len(password) < 8:
        print("Password is too short.")
        sys.exit(1)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.role = "admin"
            print(f"Existing user {email} is now an admin.")
        else:
            db.add(
                User(
                    email=email,
                    password_hash=hash_password(password),
                    full_name="Admin",
                    role="admin",
                )
            )
            print(f"Admin {email} created.")
        db.commit()


if __name__ == "__main__":
    main()