"""DTO: PartCreationDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class PartCreationDTO(BaseModel):
    """POST /workspaces/{ws}/parts 请求体。"""
    model_config = ConfigDict(populate_by_name=True, extra='forbid')
    number: str
    name: str = ""
    description: str = ""
    standard_part: bool = False
    workflow_model_id: Optional[str] = None
    template_id: Optional[str] = None
    acl: Optional[dict] = None
    role_mapping: Optional[List[dict]] = None
