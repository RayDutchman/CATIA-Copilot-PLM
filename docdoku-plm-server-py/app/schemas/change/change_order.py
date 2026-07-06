"""DTO: ChangeOrderDTO. Auto-split from change.py."""
from app.schemas.change.change_item import ChangeItemDTO
from typing import Optional, List




class ChangeOrderDTO(ChangeItemDTO):
    milestoneId: Optional[int] = None
    addressedChangeRequests: List[dict] = []
