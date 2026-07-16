"""DTO: PartCreationDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


class PartCreationDTO(BaseModel):
    """POST /workspaces/{ws}/parts 请求体。

    对齐 Payara PartCreationDTO：前端发送 camelCase，用 alias 接收。
    extra='forbid' 对齐 Java 严格校验，前端错拼字段会暴露为 422。
    """
    model_config = ConfigDict(populate_by_name=True, extra='forbid')

    number: str = Field(..., alias="partNumber")
    name: str = Field("", alias="partName")
    description: str = ""
    # 前端发 camelCase，alias 映射；同时支持 snake_case（populate_by_name=True）
    standard_part: bool = Field(False, alias="standardPart")
    workflow_model_id: Optional[str] = Field(None, alias="workflowModelId")
    template_id: Optional[str] = Field(None, alias="templateId")
    acl: Optional[dict] = None
    role_mapping: Optional[List[dict]] = Field(None, alias="roleMapping")
    # 前端 part_creation_view 在 body 中携带 workspaceId（路由已有，但保留兼容）
    workspace_id: Optional[str] = Field(None, alias="workspaceId")
