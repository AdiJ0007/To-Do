from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.user_service import get_user_by_id


def get_project_by_id(db: Session, project_id: int) -> Project | None:
    return db.get(Project, project_id)


def user_can_access_project(project: Project, user: User) -> bool:
    if user.role == "admin":
        return True
    if project.owner_id == user.id:
        return True
    return any(member.id == user.id for member in project.members)


def user_owns_project(project: Project, user: User) -> bool:
    if user.role == "admin":
        return True
    return project.owner_id == user.id


def list_projects_for_user(db: Session, user: User) -> tuple[list[Project], int]:
    owned_query = select(Project).where(Project.owner_id == user.id)
    member_query = select(Project).where(Project.members.any(User.id == user.id))
    owned = db.scalars(owned_query).all()
    members = db.scalars(member_query).all()
    unique: dict[int, Project] = {project.id: project for project in owned}
    unique.update({project.id: project for project in members})
    items = sorted(unique.values(), key=lambda project: project.created_at, reverse=True)
    return items, len(items)


def create_project(db: Session, user: User, payload: ProjectCreate) -> Project:
    project = Project(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        owner_id=user.id,
    )
    members: list[User] = [user]
    for member_id in dict.fromkeys(payload.member_ids):
        member = get_user_by_id(db, member_id)
        if member and member.id not in {existing.id for existing in members}:
            members.append(member)
    project.members = members
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, payload: ProjectUpdate) -> Project:
    updates = payload.model_dump(exclude_unset=True, exclude={"member_ids"})
    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(project, field, value)

    if payload.member_ids is not None:
        members: list[User] = []
        for member_id in dict.fromkeys(payload.member_ids):
            member = get_user_by_id(db, member_id)
            if member and member.id not in {existing.id for existing in members}:
                members.append(member)
        owner = get_user_by_id(db, project.owner_id)
        if owner and owner.id not in {existing.id for existing in members}:
            members.append(owner)
        project.members = members

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()


def add_members_to_project(db: Session, project: Project, member_ids: list[int]) -> Project:
    member_map = {member.id: member for member in project.members}
    owner = get_user_by_id(db, project.owner_id)
    if owner:
        member_map[owner.id] = owner
    for member_id in member_ids:
        member = get_user_by_id(db, member_id)
        if member:
            member_map[member.id] = member
    project.members = list(member_map.values())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def remove_member_from_project(db: Session, project: Project, member_id: int) -> Project:
    if project.owner_id == member_id:
        return project
    project.members = [member for member in project.members if member.id != member_id]
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
