"""DTO: PartTemplateDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class PartTemplateDTO(BaseModel):
    """零件模板 CRUD 响应，字段与 DocdokuPLM PartMasterTemplateDTO 一致"""
    model_config = ConfigDict(from_attributes=True, extra='forbid')
    id: str = ""
    workspaceId: Optional[str] = None
    mask: Optional[str] = None
    idGenerated: Optional[bool] = False
    partType: Optional[str] = None
    attributesLocked: Optional[bool] = False
    author: Optional[dict] = None
    creationDate: Optional[str] = None
    modificationDate: Optional[str] = None
    acl: Optional[dict] = None
    workflowModelId: Optional[str] = None
    attributeTemplates: list = []
    attributeInstanceTemplates: list = []
