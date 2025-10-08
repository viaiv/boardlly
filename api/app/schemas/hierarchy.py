from pydantic import BaseModel, Field


class HierarchyItemResponse(BaseModel):
    """Schema for a single item in the hierarchy tree."""
    id: int
    item_node_id: str
    title: str | None
    item_type: str | None = Field(None, description="story, task, feature, bug")
    status: str | None
    epic_name: str | None
    parent_item_id: int | None
    labels: list[str] | None
    children: list["HierarchyItemResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class HierarchyEpicResponse(BaseModel):
    """Schema for an epic group in the hierarchy."""
    epic_option_id: str | None
    epic_name: str | None
    items: list[HierarchyItemResponse]


class HierarchyResponse(BaseModel):
    """Schema for complete hierarchy response."""
    epics: list[HierarchyEpicResponse]
    orphans: list[HierarchyItemResponse] = Field(
        default_factory=list,
        description="Items sem épico definido"
    )


# Needed for self-referential model
HierarchyItemResponse.model_rebuild()
