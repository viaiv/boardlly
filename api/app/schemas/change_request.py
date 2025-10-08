"""
Schemas Pydantic para ChangeRequest (Solicitações de Mudança).

Define os contratos de entrada e saída da API para o fluxo:
Editor cria → PM aprova/rejeita → Issue criada no GitHub
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChangeRequestCreate(BaseModel):
    """Payload para criar uma nova solicitação"""

    title: str = Field(min_length=3, max_length=500, description="Título da solicitação")
    description: Optional[str] = Field(None, description="Descrição detalhada")
    impact: Optional[str] = Field(
        None, description="Impacto esperado da mudança"
    )
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high|urgent)$",
        description="Prioridade: low, medium, high, urgent",
    )
    request_type: Optional[str] = Field(
        None,
        pattern="^(feature|bug|tech_debt|docs)$",
        description="Tipo: feature, bug, tech_debt, docs",
    )
    suggested_epic: Optional[str] = Field(None, description="Épico sugerido (nome)")
    suggested_iteration: Optional[str] = Field(None, description="Sprint sugerida (nome)")
    suggested_estimate: Optional[float] = Field(
        None, ge=0, description="Estimativa sugerida (story points)"
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Título não pode ser vazio")
        return v.strip()


class ChangeRequestUpdate(BaseModel):
    """Payload para atualizar uma solicitação existente"""

    title: Optional[str] = Field(None, min_length=3, max_length=500)
    description: Optional[str] = None
    impact: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    request_type: Optional[str] = Field(
        None, pattern="^(feature|bug|tech_debt|docs)$"
    )
    suggested_epic: Optional[str] = None
    suggested_iteration: Optional[str] = None
    suggested_estimate: Optional[float] = Field(None, ge=0)


class ChangeRequestApprove(BaseModel):
    """Payload para aprovar uma solicitação e criar Issue"""

    review_notes: Optional[str] = Field(None, description="Notas da revisão")
    create_issue: bool = Field(
        default=True, description="Criar Issue automaticamente no GitHub?"
    )
    add_to_project: bool = Field(
        default=True, description="Adicionar Issue ao Project automaticamente?"
    )

    # Permite PM sobrescrever valores sugeridos
    epic_option_id: Optional[str] = Field(
        None, description="ID da opção de épico (override)"
    )
    iteration_id: Optional[str] = Field(
        None, description="ID da iteração/sprint (override)"
    )
    estimate: Optional[float] = Field(None, ge=0, description="Estimativa (override)")


class ChangeRequestReject(BaseModel):
    """Payload para rejeitar uma solicitação"""

    review_notes: str = Field(
        min_length=1, description="Motivo da rejeição (obrigatório)"
    )

    @field_validator("review_notes")
    @classmethod
    def notes_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Notas de rejeição são obrigatórias")
        return v.strip()


class ChangeRequestResponse(BaseModel):
    """Resposta completa de uma solicitação"""

    model_config = {"from_attributes": True}

    id: UUID
    account_id: UUID
    created_by: UUID
    creator_name: Optional[str] = Field(None, description="Nome do criador (via join)")

    # Conteúdo
    title: str
    description: Optional[str] = None
    impact: Optional[str] = None

    # Classificação
    priority: str
    request_type: Optional[str] = None

    # Workflow
    status: str  # pending/approved/rejected/converted
    reviewed_by: Optional[UUID] = None
    reviewer_name: Optional[str] = Field(None, description="Nome do revisor (via join)")
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

    # Conversão
    github_issue_node_id: Optional[str] = None
    github_issue_number: Optional[int] = None
    github_issue_url: Optional[str] = None
    converted_at: Optional[datetime] = None

    # Metadados sugeridos
    suggested_epic: Optional[str] = None
    suggested_iteration: Optional[str] = None
    suggested_estimate: Optional[float] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime


class ChangeRequestListResponse(BaseModel):
    """Resposta simplificada para listagem"""

    model_config = {"from_attributes": True}

    id: UUID
    title: str
    priority: str
    status: str
    request_type: Optional[str] = None
    creator_name: Optional[str] = None
    github_issue_number: Optional[int] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
