"""文档相关 Pydantic DTO，字段名与 DocdokuPLM JSON 响应完全一致（camelCase）。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.part import UserDTO

# Re-exports from split files
from app.schemas.document.document_iteration import DocumentIterationDTO  # noqa: E402, F401
from app.schemas.document.document_revision import DocumentRevisionDTO  # noqa: E402, F401
from app.schemas.document.document_master_template import DocumentTemplateDTO  # noqa: E402, F401
from app.schemas.document.baselined_document import BaselinedDocumentDTO  # noqa: E402, F401
from app.schemas.document.document_baseline import DocumentBaselineDTO  # noqa: E402, F401
from app.schemas.document.folder import FolderDTO  # noqa: E402, F401

UserDTO.model_rebuild()
DocumentIterationDTO.model_rebuild()
DocumentRevisionDTO.model_rebuild()
DocumentTemplateDTO.model_rebuild()
BaselinedDocumentDTO.model_rebuild()
DocumentBaselineDTO.model_rebuild()
FolderDTO.model_rebuild()
