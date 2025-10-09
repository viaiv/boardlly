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
    epic_option_id: str | None = None
    epic_name: str | None = None
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


class StatusBreakdownEntry(BaseModel):
    status: str | None = None
    count: int
    total_estimate: float | None = None


class IterationSummaryResponse(BaseModel):
    iteration_id: str | None = None
    name: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    item_count: int
    completed_count: int
    total_estimate: float | None = None
    completed_estimate: float | None = None
    status_breakdown: list[StatusBreakdownEntry] = Field(default_factory=list)


class IterationOptionResponse(BaseModel):
    id: str
    name: str
    start_date: datetime | None = None
    end_date: datetime | None = None


class IterationDashboardResponse(BaseModel):
    summaries: list[IterationSummaryResponse] = Field(default_factory=list)
    options: list[IterationOptionResponse] = Field(default_factory=list)


class EpicSummaryResponse(BaseModel):
    epic_option_id: str | None = None
    name: str | None = None
    item_count: int
    completed_count: int
    total_estimate: float | None = None
    completed_estimate: float | None = None
    status_breakdown: list[StatusBreakdownEntry] = Field(default_factory=list)


class EpicOptionResponse(BaseModel):
    id: int
    name: str = Field(validation_alias="option_name")
    color: str | None = None
    description: str | None = None

    class Config:
        from_attributes = True
        populate_by_name = True


class EpicOptionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    color: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=500)


class EpicOptionUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    color: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=500)


class EpicDashboardResponse(BaseModel):
    summaries: list[EpicSummaryResponse] = Field(default_factory=list)
    options: list[EpicOptionResponse] = Field(default_factory=list)


class EpicDetailResponse(BaseModel):
    """Épico completo com descrição, progresso e sub-issues"""
    id: int
    item_node_id: str
    content_node_id: str | None = None
    epic_option_id: str | None = None  # ID da opção no campo Epic
    epic_option_name: str | None = None  # Nome da opção no campo Epic
    title: str
    description: str | None = None
    url: str | None = None
    state: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    labels: list[dict] = Field(default_factory=list)

    # Métricas de progresso
    total_issues: int = 0
    completed_issues: int = 0
    progress_percentage: float = 0.0
    total_estimate: float | None = None
    completed_estimate: float | None = None

    # Sub-issues vinculadas
    linked_issues: list[int] = Field(default_factory=list)  # IDs das issues vinculadas


class EpicCreateRequest(BaseModel):
    """Request para criar um novo épico (issue) no GitHub"""
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=65536)
    repository: str = Field(min_length=1, max_length=255)  # Nome do repositório (ex: "meu-repo")
    epic_option_id: str | None = None  # ID da opção Epic para vincular
    labels: list[str] = Field(default_factory=list)  # Labels opcionais


class EpicCreateResponse(BaseModel):
    """Response após criar épico"""
    issue_number: int
    issue_url: str
    issue_node_id: str


class StoryCreateRequest(BaseModel):
    """Request para criar uma nova história (issue) no GitHub"""
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=65536)
    repository: str = Field(min_length=1, max_length=255)  # Nome do repositório (ex: "meu-repo")
    epic_option_id: str | None = None  # ID da opção Epic para vincular (obrigatório para histórias)
    labels: list[str] = Field(default_factory=list)  # Labels opcionais


class StoryCreateResponse(BaseModel):
    """Response após criar história"""
    issue_number: int
    issue_url: str
    issue_node_id: str
