from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.todo import PriorityLevel
from app.schemas.user import UserRead


class TodoBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    completed: bool = False
    priority: PriorityLevel = PriorityLevel.MEDIUM
    due_date: datetime | None = None
    project_id: int | None = None
    assignee_ids: list[int] = Field(default_factory=list)


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    completed: bool | None = None
    priority: PriorityLevel | None = None
    due_date: datetime | None = None
    project_id: int | None = None
    assignee_ids: list[int] | None = None


class TodoRead(TodoBase):
    id: int
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    assignees: list[UserRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TodoListResponse(BaseModel):
    items: list[TodoRead]
    total: int
    skip: int
    limit: int


class TodoStats(BaseModel):
    total: int
    completed: int
    pending: int
    high_priority: int
