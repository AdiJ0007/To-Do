from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectMemberUpdate,
    ProjectRead,
    ProjectUpdate,
)
from app.services.project_service import (
    add_members_to_project,
    create_project,
    delete_project,
    get_project_by_id,
    list_projects_for_user,
    remove_member_from_project,
    update_project,
    user_can_access_project,
    user_owns_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project_item(
    payload: ProjectCreate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    return create_project(db, current_user, payload)


@router.get("", response_model=ProjectListResponse)
def list_project_items(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectListResponse:
    items, total = list_projects_for_user(db, current_user)
    return ProjectListResponse(items=items, total=total)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project_item(
    project_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not user_can_access_project(project, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project_item(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not user_owns_project(project, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can update this project")
    return update_project(db, project, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_item(
    project_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not user_owns_project(project, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can delete this project")
    delete_project(db, project)


@router.post("/{project_id}/members", response_model=ProjectRead)
def add_project_members(
    project_id: int,
    payload: ProjectMemberUpdate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not user_owns_project(project, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can change members")
    return add_members_to_project(db, project, payload.member_ids)


@router.delete("/{project_id}/members/{member_id}", response_model=ProjectRead)
def remove_project_member(
    project_id: int,
    member_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not user_owns_project(project, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can change members")
    return remove_member_from_project(db, project, member_id)
