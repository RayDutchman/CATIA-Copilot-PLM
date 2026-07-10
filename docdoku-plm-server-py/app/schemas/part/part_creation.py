"""DTO: PartCreationDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


class PartCreationDTO(BaseModel):
    """POST /workspaces/{ws}/parts 请求体。

    对齐 Payara PartCreationDTO：前端发送 camelCase，用 alias 接收。
    extra='ignore' 防止未知字段报 422（如 workspaceId 由路由参数提供，body 中忽略即可）。
    """
    model_config = ConfigDict(populate_by_name=True, extra='ignore')

    number: str
    name: str = ""
    description: str = ""
    # 前端发 camelCase，alias 映射；同时支持 snake_case（populate_by_name=True）
    standard_part: bool = Field(False, alias="standardPart")
    workflow_model_id: Optional[str] = Field(None, alias="workflowModelId")
    template_id: Optional[str] = Field(None, alias="templateId")
    acl: Optional[dict] = None
    role_mapping: Optional[List[dict]] = Field(None, alias="roleMapping")
