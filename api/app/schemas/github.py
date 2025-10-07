from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GithubTokenRequest(BaseModel):
    token: str = Field(min_length=10)


class GithubProjectRequest(BaseModel):
    owner: str = Field(min_length=1)
    project_number: int = Field(ge=1)


class GithubProjectResponse(BaseModel):
    id: int
    owner_login: str
    project_number: int
    project_node_id: str
    name: str | None = None
    field_mappings: dict | None = None
    last_synced_at: datetime | None = None
    status_columns: list[str] | None = None

    class Config:
        from_attributes = True


class GithubProjectSummary(BaseModel):
    node_id: str
    number: int
    title: str | None = None
    updated_at: datetime | None = None


class ProjectItemResponse(BaseModel):
    id: int
    item_node_id: str
    content_type: str | None = None
    title: str | None = None
    status: str | None = None
    iteration: str | None = None
    iteration_id: str | None = None
    iteration_start: datetime | None = None
    iteration_end: datetime | None = None
    estimate: float | None = None
    url: str | None = None
    assignees: list[str] = Field(default_factory=list)
    start_date: datetime | None = None
    end_date: datetime | None = None
    due_date: datetime | None = None
    updated_at: datetime | None = None
    remote_updated_at: datetime | None = None
    last_synced_at: datetime | None = None
    last_local_edit_at: datetime | None = None
    last_local_edit_by: UUID | None = None
    field_values: dict | None = None
    epic_option_id: str | None = None
    epic_name: str | None = None

    class Config:
        from_attributes = True


class ProjectItemUpdateRequest(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    due_date: datetime | None = None
    iteration_id: str | None = None
    iteration_title: str | None = None
    status: str | None = None
    remote_updated_at: datetime | None = None


class ProjectItemCommentResponse(BaseModel):
    id: str
    author: str | None = None
    author_url: str | None = None
    author_avatar_url: str | None = None
    body: str
    url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProjectItemLabelResponse(BaseModel):
    name: str
    color: str | None = None


class ProjectItemAuthorResponse(BaseModel):
    login: str | None = None
    url: str | None = None
    avatar_url: str | None = None


class ProjectItemDetailResponse(BaseModel):
    id: str
    content_type: str | None = None
    number: int | None = None
    title: str | None = None
    body: str | None = None
    body_text: str | None = None
    state: str | None = None
    url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    merged: bool | None = None
    author: ProjectItemAuthorResponse | None = None
    labels: list[ProjectItemLabelResponse] = Field(default_factory=list)
