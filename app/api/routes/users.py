from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.schemas.user import UserListResponse, UserRead
from app.services.user_service import list_users
from app.services.user_service import get_user_by_id, set_user_role
from fastapi import HTTPException, status

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> UserListResponse:
    items, total = list_users(db, skip=skip, limit=limit)
    return UserListResponse(items=items, total=total)


@router.patch("/{user_id}/role", response_model=UserRead)
def update_user_role(user_id: int, payload: dict, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    # Only admins can change roles
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can change roles")
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    role = payload.get("role")
    if role not in ("admin", "member"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    updated = set_user_role(db, user, role)
    return updated
