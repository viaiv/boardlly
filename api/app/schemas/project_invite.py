from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectInviteResponse(BaseModel):
    id: int
    project_id: int
    invited_email: str
    invited_by_user_id: UUID
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    # Project information (joined)
    project_name: str | None = None
    project_owner: str | None = None
    project_number: int | None = None

    # Inviter information (joined)
    invited_by_email: str | None = None
    invited_by_name: str | None = None

    class Config:
        from_attributes = True


class ProjectInviteCreateRequest(BaseModel):
    email: str = Field(description="Email do usuário a ser convidado")
    role: str = Field(default="viewer", description="Role que o usuário terá no projeto (viewer, editor, pm, admin)")


class ProjectInviteListResponse(BaseModel):
    id: int
    project_id: int
    project_name: str | None
    project_owner: str | None
    project_number: int | None
    invited_email: str
    invited_by_user_id: UUID
    invited_by_email: str
    invited_by_name: str | None
    role: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
