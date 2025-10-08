from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

UserRole = Literal["viewer", "editor", "pm", "admin", "owner"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: Optional[str] = None
    role: UserRole = "viewer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: Optional[str] = None
    role: UserRole
    account_id: Optional[UUID] = None
    needs_account_setup: bool = False

    class Config:
        from_attributes = True


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, description="Token de verificação recebido por email")


class ResendVerificationRequest(BaseModel):
    email: EmailStr
