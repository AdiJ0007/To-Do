from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import mapped_column, relationship

from app.core.database import Base
from app.models.association import project_members


class Project(Base):
    __tablename__ = "projects"

    id = mapped_column(Integer, primary_key=True, index=True)
    name = mapped_column(String(255), nullable=False, index=True)
    description = mapped_column(Text, nullable=True)
    owner_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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

    owner = relationship("User", back_populates="owned_projects")
    members = relationship(
        "User",
        secondary=project_members,
        back_populates="project_memberships",
        lazy="selectin",
    )
    todos = relationship("Todo", back_populates="project", cascade="all, delete-orphan")
