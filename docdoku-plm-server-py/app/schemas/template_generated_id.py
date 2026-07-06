"""DTO: TemplateGeneratedIdDTO."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TemplateGeneratedIdDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: Optional[str] = None
