from datetime import datetime, date
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("Member", back_populates="team", cascade="all,delete")


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    career_level = Column(String(100), nullable=False)
    is_lead = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow)

    team = relationship("Team", back_populates="members")
    tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.creator_id")
    tagged_tasks = relationship("TaskTag", back_populates="member")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    hours_spent = Column(Numeric(6, 2), nullable=True)
    due_date = Column(Date, nullable=True)
    blockers = Column(Text, nullable=True)
    comments = Column(Text, nullable=True)
    status = Column(String(50), default="in_progress")
    assignee_id = Column(Integer, ForeignKey("members.id", ondelete="SET NULL"))
    creator_id = Column(Integer, ForeignKey("members.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignee = relationship("Member", back_populates="tasks", foreign_keys=[assignee_id])
    creator = relationship("Member", back_populates="created_tasks", foreign_keys=[creator_id])
    tags = relationship("TaskTag", back_populates="task", cascade="all,delete")


class TaskTag(Base):
    __tablename__ = "task_tags"
    __table_args__ = (UniqueConstraint("task_id", "member_id", name="uq_task_member_tag"),)

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="tags")
    member = relationship("Member", back_populates="tagged_tasks")


class SessionToken(Base):
    __tablename__ = "session_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, nullable=False)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"))
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member")