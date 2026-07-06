"""变更管理相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应完全一致（camelCase）。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class AffectedPartDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    partKey: Optional[str] = None
    partNumber: Optional[str] = None
    version: Optional[str] = None


class AffectedDocumentDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    documentKey: Optional[str] = None
    documentMasterId: Optional[str] = None
    version: Optional[str] = None

# Re-exports from split files
from app.schemas.change.change_issue import ChangeIssueDTO  # noqa: E402, F401
from app.schemas.change.change_item import ChangeItemDTO  # noqa: E402, F401
from app.schemas.change.change_order import ChangeOrderDTO  # noqa: E402, F401
from app.schemas.change.change_request import ChangeRequestDTO  # noqa: E402, F401
from app.schemas.change.milestone import MilestoneDTO  # noqa: E402, F401

ChangeIssueDTO.model_rebuild()
ChangeItemDTO.model_rebuild()
ChangeOrderDTO.model_rebuild()
ChangeRequestDTO.model_rebuild()
MilestoneDTO.model_rebuild()
