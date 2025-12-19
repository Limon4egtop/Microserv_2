from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)

class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str
    roles: list[str]
    created_at: str
    updated_at: str

class PagedUsers(BaseModel):
    items: list[UserPublic]
    page: int
    page_size: int
    total: int
