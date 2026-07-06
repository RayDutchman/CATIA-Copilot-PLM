"""DTO: ComponentDTO. Auto-split from part.py."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class ComponentDTO(BaseModel):
    """递归 BOM 节点，与 Payara ComponentDTO 字段完全一致。"""
    model_config = ConfigDict(extra='forbid')
    number: str
    name: str = ""
    version: Optional[str] = None
    iteration: int = 0
    assembly: bool = False
    substitute: bool = False
    optional: bool = False
    amount: float = 0
    unit: Optional[str] = None
    partUsageLinkId: Optional[str] = None
    partUsageLinkReferenceDescription: Optional[str] = None
    components: List[ComponentDTO] = []
    attributes: List[dict] = []
    checkOutUser: Optional[UserDTO] = None
    checkOutDate: Optional[datetime] = None
    released: bool = False
    obsolete: bool = False
    lastIterationNumber: Optional[int] = None
    accessDeny: bool = False
    hasPathData: bool = False
    isVirtual: bool = False
    standardPart: bool = False
    description: Optional[str] = None
    author: Optional[str] = None
    authorLogin: Optional[str] = None
    path: Optional[str] = None
