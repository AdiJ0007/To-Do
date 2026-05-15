from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import mapped_column, relationship

from app.core.database import Base
from app.models.association import project_members, todo_assignees


class User(Base):
    __tablename__ = "users"

    id = mapped_column(Integer, primary_key=True, index=True)
    name = mapped_column(String(120), nullable=False)
    email = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash = mapped_column(String(255), nullable=False)
    role = mapped_column(String(32), nullable=False, default="member")
    created_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    owned_projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    project_memberships = relationship(
        "Project",
        secondary=project_members,
        back_populates="members",
        lazy="selectin",
    )
    created_todos = relationship("Todo", back_populates="created_by")
    assigned_todos = relationship(
        "Todo",
        secondary=todo_assignees,
        back_populates="assignees",
        lazy="selectin",
    )
