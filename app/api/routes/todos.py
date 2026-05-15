from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.models.todo import PriorityLevel
from app.schemas.todo import (
    TodoCreate,
    TodoListResponse,
    TodoRead,
    TodoStats,
    TodoUpdate,
)
from app.services.todo_service import (
    create_todo,
    delete_todo,
    get_todo_by_id,
    list_todos,
    todo_stats,
    user_can_access_todo,
    update_todo,
)

router = APIRouter(prefix="/todos", tags=["todos"])


@router.post("", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
def create_todo_item(
    payload: TodoCreate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TodoRead:
    try:
        return create_todo(db, current_user, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("", response_model=TodoListResponse)
def list_todo_items(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    completed: bool | None = Query(default=None),
    priority: PriorityLevel | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=255),
    project_id: int | None = Query(default=None, ge=1),
    sort_by: Literal["title", "created_at", "updated_at", "due_date"] = Query(
        default="created_at"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TodoListResponse:
    items, total = list_todos(
        db,
        user=current_user,
        skip=skip,
        limit=limit,
        completed=completed,
        priority=priority,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        project_id=project_id,
    )
    return TodoListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/stats", response_model=TodoStats)
def get_todo_stats(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TodoStats:
    stats = todo_stats(db, current_user)
    return TodoStats(**stats)


@router.get("/{todo_id}", response_model=TodoRead)
def get_todo_item(
    todo_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TodoRead:
    todo = get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    if not user_can_access_todo(todo, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return todo


@router.patch("/{todo_id}", response_model=TodoRead)
def update_todo_item(
    todo_id: int,
    payload: TodoUpdate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TodoRead:
    todo = get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    if not user_can_access_todo(todo, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        return update_todo(db, todo, payload, current_user)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo_item(
    todo_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    todo = get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    if not user_can_access_todo(todo, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    delete_todo(db, todo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
