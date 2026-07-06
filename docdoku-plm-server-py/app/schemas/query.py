"""DTO: QueryDTO."""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class QueryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[int] = None
    name: Optional[str] = None
    creationDate: Optional[datetime] = None
    queryRule: Optional["QueryRuleDTO"] = None
    pathDataQueryRule: Optional["QueryRuleDTO"] = None
    selects: List[str] = []
    orderByList: List[str] = []
    groupedByList: List[str] = []
    contexts: List["QueryContextDTO"] = []


from app.schemas.query_rule import QueryRuleDTO  # noqa: E402
from app.schemas.query_context import QueryContextDTO  # noqa: E402

QueryDTO.model_rebuild()
