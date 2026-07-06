"""DTO: QueryRuleDTO."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class QueryRuleDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    condition: Optional[str] = None
    id: Optional[str] = None
    field: Optional[str] = None
    type: Optional[str] = None
    operator: Optional[str] = None
    values: List[str] = []
    rules: List["QueryRuleDTO"] = []


QueryRuleDTO.model_rebuild()
