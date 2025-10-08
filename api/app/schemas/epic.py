from pydantic import BaseModel, Field


class EpicOptionBase(BaseModel):
    """Base schema for Epic option."""
    option_name: str = Field(min_length=1, max_length=255, description="Nome do épico")
    color: str | None = Field(None, max_length=50, description="Cor do épico (hex ou nome)")
    description: str | None = Field(None, max_length=500, description="Descrição do épico")


class EpicOptionCreate(EpicOptionBase):
    """Schema for creating a new Epic option."""
    pass


class EpicOptionUpdate(BaseModel):
    """Schema for updating an Epic option."""
    option_name: str | None = Field(None, min_length=1, max_length=255)
    color: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=500)


class EpicOptionResponse(EpicOptionBase):
    """Schema for Epic option response."""
    id: int
    project_id: int
    option_id: str

    class Config:
        from_attributes = True
