from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class AccountCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class AccountResponse(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True
