"""DTO: ChangeRequestDTO. Auto-split from change.py."""
from app.schemas.change.change_item import ChangeItemDTO
from typing import Optional, List




class ChangeRequestDTO(ChangeItemDTO):
    milestoneId: Optional[int] = None
    addressedChangeIssues: List[dict] = []
