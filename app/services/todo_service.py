from collections.abc import Sequence

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.association import project_members
from app.models.todo import PriorityLevel, Todo
from app.models.user import User
from app.schemas.todo import TodoCreate, TodoUpdate
from app.services.project_service import get_project_by_id, user_can_access_project
from app.services.user_service import get_user_by_id


SORTABLE_FIELDS = {
    "title": Todo.title,
    "created_at": Todo.created_at,
    "updated_at": Todo.updated_at,
    "due_date": Todo.due_date,
}


def _load_assignees(db: Session, assignee_ids: list[int]) -> list[User]:
    assignees: list[User] = []
    for assignee_id in dict.fromkeys(assignee_ids):
        assignee = get_user_by_id(db, assignee_id)
        if assignee and assignee.id not in {existing.id for existing in assignees}:
            assignees.append(assignee)
    return assignees


def _visible_todo_query(db: Session, user: User) -> Select[tuple[Todo]]:
    from app.models.project import Project
    
    # Admins see: todos in projects they own + todos assigned to them
    # Members see: only todos assigned to them
    if user.role == "admin":
        admin_project_ids = select(Project.id).where(Project.owner_id == user.id)
        return select(Todo).where(
            or_(
                Todo.project_id.in_(admin_project_ids),
                Todo.assignees.any(User.id == user.id),
            )
        )
    else:
        # Members/taskers only see tasks assigned to them
        return select(Todo).where(
            Todo.assignees.any(User.id == user.id)
        )


def create_todo(db: Session, user: User, payload: TodoCreate) -> Todo:
    if payload.project_id is not None:
        project = get_project_by_id(db, payload.project_id)
        if project is None or not user_can_access_project(project, user):
            raise ValueError("Project not found or access denied")

    todo = Todo(
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        completed=payload.completed,
        priority=payload.priority,
        due_date=payload.due_date,
        project_id=payload.project_id,
        created_by_id=user.id,
    )
    todo.assignees = _load_assignees(db, payload.assignee_ids)
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


def get_todo_by_id(db: Session, todo_id: int) -> Todo | None:
    return db.get(Todo, todo_id)


def user_can_access_todo(todo: Todo, user: User) -> bool:
    if todo.created_by_id == user.id:
        return True
    if any(assignee.id == user.id for assignee in todo.assignees):
        return True
    if todo.project and user_can_access_project(todo.project, user):
        return True
    return False


def list_todos(
    db: Session,
    *,
    user: User,
    skip: int,
    limit: int,
    completed: bool | None,
    priority: PriorityLevel | None,
    search: str | None,
    sort_by: str,
    sort_order: str,
    project_id: int | None,
) -> tuple[Sequence[Todo], int]:
    base_query: Select[tuple[Todo]] = _visible_todo_query(db, user)

    if completed is not None:
        base_query = base_query.where(Todo.completed == completed)
    if priority is not None:
        base_query = base_query.where(Todo.priority == priority)
    if project_id is not None:
        base_query = base_query.where(Todo.project_id == project_id)
    if search:
        term = f"%{search.strip()}%"
        base_query = base_query.where(or_(Todo.title.ilike(term), Todo.description.ilike(term)))

    total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0

    sort_column = SORTABLE_FIELDS[sort_by]
    ordering = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    rows = db.scalars(base_query.order_by(ordering).offset(skip).limit(limit)).all()
    return rows, int(total)


def update_todo(db: Session, todo: Todo, payload: TodoUpdate, user: User) -> Todo:
    updates = payload.model_dump(exclude_unset=True, exclude={"assignee_ids"})
    if "project_id" in updates and updates["project_id"] is not None:
        project = get_project_by_id(db, int(updates["project_id"]))
        if project is None or not user_can_access_project(project, user):
            raise ValueError("Project not found or access denied")

    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(todo, field, value)

    if payload.assignee_ids is not None:
        todo.assignees = _load_assignees(db, payload.assignee_ids)

    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


def delete_todo(db: Session, todo: Todo) -> None:
    db.delete(todo)
    db.commit()


def todo_stats(db: Session, user: User) -> dict[str, int]:
    visible_todos = _visible_todo_query(db, user).subquery()
    total = db.scalar(select(func.count()).select_from(visible_todos)) or 0
    completed = (
        db.scalar(select(func.count()).select_from(visible_todos).where(visible_todos.c.completed.is_(True)))
        or 0
    )
    high_priority = (
        db.scalar(select(func.count()).select_from(visible_todos).where(visible_todos.c.priority == PriorityLevel.HIGH))
        or 0
    )
    return {
        "total": int(total),
        "completed": int(completed),
        "pending": int(total - completed),
        "high_priority": int(high_priority),
    }
