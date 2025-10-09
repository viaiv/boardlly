from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectRepositoryResponse(BaseModel):
    id: int
    project_id: int
    owner: str
    repo_name: str
    repo_node_id: str | None = None
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectRepositoryCreateRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=255)
    repo_name: str = Field(min_length=1, max_length=255)
    is_primary: bool = False


class ProjectRepositoryUpdateRequest(BaseModel):
    is_primary: bool | None = None
