from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import mapped_column, relationship

from app.core.database import Base
from app.models.association import todo_assignees


class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Todo(Base):
    __tablename__ = "todos"

    id = mapped_column(Integer, primary_key=True, index=True)
    title = mapped_column(String(255), nullable=False, index=True)
    description = mapped_column(Text, nullable=True)
    completed = mapped_column(Boolean, nullable=False, default=False, index=True)
    project_id = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    priority = mapped_column(
        SqlEnum(PriorityLevel),
        nullable=False,
        default=PriorityLevel.MEDIUM,
        index=True,
    )
    due_date = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    project = relationship("Project", back_populates="todos")
    created_by = relationship("User", back_populates="created_todos")
    assignees = relationship(
        "User",
        secondary=todo_assignees,
        back_populates="assigned_todos",
        lazy="selectin",
    )
