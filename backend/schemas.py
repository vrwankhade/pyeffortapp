from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TeamBase(BaseModel):
    name: str


class TeamCreate(TeamBase):
    pass


class Team(TeamBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MemberBase(BaseModel):
    username: str
    name: str
    career_level: str
    is_lead: bool = False
    team_id: Optional[int] = None


class MemberCreate(MemberBase):
    password: str


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    career_level: Optional[str] = None
    is_lead: Optional[bool] = None
    team_id: Optional[int] = None
    password: Optional[str] = None
    is_locked: Optional[bool] = None


class Member(MemberBase):
    id: int
    created_at: datetime
    is_locked: bool = False
    team_name: Optional[str] = None

    class Config:
        from_attributes = True


class MemberLogin(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    member: Member


class TaskBase(BaseModel):
    title: str
    details: Optional[str] = None
    hours_spent: Optional[float] = Field(None, ge=0)
    due_date: Optional[date] = None
    blockers: Optional[str] = None
    comments: Optional[str] = None
    status: str = "in_progress"
    assignee_id: Optional[int] = None


class TaskCreate(TaskBase):
    tags: List[int] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    details: Optional[str] = None
    hours_spent: Optional[float] = Field(None, ge=0)
    due_date: Optional[date] = None
    blockers: Optional[str] = None
    comments: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[int] = None
    tags: Optional[List[int]] = None


class Task(TaskBase):
    id: int
    creator_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    tags: List[int] = []

    class Config:
        from_attributes = True


class TaskTagCreate(BaseModel):
    member_id: int