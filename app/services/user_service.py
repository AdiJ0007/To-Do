import re
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import SignUpRequest


def detect_role_from_email(email: str) -> str:
    """
    Detect user role based on email format.
    Admin: <name>.admin@<domain>.com
    Member/Tasker: <name>.member@<domain>.com or any other format defaults to member
    """
    email_lower = email.strip().lower()
    if ".admin@" in email_lower:
        return "admin"
    elif ".member@" in email_lower:
        return "member"
    else:
        return "member"  # Default to member for other formats


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = email.strip().lower()
    return db.scalar(select(User).where(User.email == normalized_email))


def create_user(db: Session, payload: SignUpRequest) -> User:
    normalized_email = payload.email.strip().lower()
    detected_role = detect_role_from_email(normalized_email)
    user = User(
        name=payload.name.strip(),
        email=normalized_email,
        password_hash=hash_password(payload.password),
        role=detected_role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def upsert_oauth_user(db: Session, *, name: str, email: str) -> User:
    normalized_email = email.strip().lower()
    cleaned_name = name.strip() or normalized_email.split("@", 1)[0]
    detected_role = detect_role_from_email(normalized_email)
    user = get_user_by_email(db, normalized_email)

    if user is None:
        user = User(
            name=cleaned_name,
            email=normalized_email,
            password_hash=hash_password(normalized_email + ":google"),
            role=detected_role,
        )
        db.add(user)
    else:
        user.name = cleaned_name

    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, *, skip: int, limit: int) -> tuple[list[User], int]:
    total = db.scalar(select(func.count(User.id))) or 0
    items = db.scalars(
        select(User).order_by(User.name.asc()).offset(skip).limit(limit)
    ).all()
    return items, int(total)


def set_user_role(db: Session, user: User, role: str) -> User:
    if role not in ("admin", "member"):
        raise ValueError("Invalid role")
    user.role = role
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
