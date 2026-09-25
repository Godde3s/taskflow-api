"""Pydantic v2 DTOs — request/response contracts."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128,
                          description="8+ chars; bcrypt-hashed server side")
    full_name: str = Field(default="", max_length=120)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


# ---------- tasks ----------
class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    status: str = Field(default="todo", pattern="^(todo|doing|done)$")
    priority: int = Field(default=2, ge=1, le=3)
    due_date: datetime | None = None


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, pattern="^(todo|doing|done)$")
    priority: int | None = Field(default=None, ge=1, le=3)
    due_date: datetime | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
    title: str
    description: str
    status: str
    priority: int
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


class Page(BaseModel):
    items: list[TaskOut]
    total: int
    page: int
    size: int


# ---------- admin ----------
class StatsOut(BaseModel):
    users: int
    tasks: int
    tasks_done: int
