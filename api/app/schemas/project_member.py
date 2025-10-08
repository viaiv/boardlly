from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectMemberResponse(BaseModel):
    id: int
    user_id: UUID
    project_id: int
    role: str
    created_at: datetime
    updated_at: datetime

    # User information (joined)
    user_email: str | None = None
    user_name: str | None = None

    class Config:
        from_attributes = True


class ProjectMemberCreateRequest(BaseModel):
    user_id: UUID = Field(description="ID do usuário a ser adicionado ao projeto")
    role: str = Field(default="viewer", description="Role do usuário no projeto (viewer, editor, pm, admin)")


class ProjectMemberUpdateRequest(BaseModel):
    role: str = Field(description="Novo role do usuário no projeto (viewer, editor, pm, admin)")
