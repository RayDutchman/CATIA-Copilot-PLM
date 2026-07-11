"""DTO: WorkspaceWorkflowCreationDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class WorkspaceWorkflowCreationDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: Optional[str] = None
    workflowModelId: Optional[str] = None
    roleMapping: List["RoleMappingDTO"] = []
    workflow: Optional[dict] = None


from app.schemas.role_mapping import RoleMappingDTO  # noqa: E402

WorkspaceWorkflowCreationDTO.model_rebuild()
