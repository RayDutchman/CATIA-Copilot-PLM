"""DTO: PathToPathLinkDTO。

对齐 Payara PathToPathLinkDTO 字段：
  id, type, description, sourceComponents, targetComponents
sourceComponents/targetComponents 是 LightPartLinkDTO 列表（路径解码后的零件链接列表）。
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PathToPathLinkDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[int] = None
    # 链接类型（用户自定义，如 "wire"/"pipe"）
    type: Optional[str] = None
    # 链接描述
    description: Optional[str] = None
    # 源路径解码后的零件链接列表（LightPartLinkDTO）
    sourceComponents: List[dict] = []
    # 目标路径解码后的零件链接列表
    targetComponents: List[dict] = []
