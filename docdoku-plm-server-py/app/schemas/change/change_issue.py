"""DTO: ChangeIssueDTO. Auto-split from change.py."""
from app.schemas.change.change_item import ChangeItemDTO
from typing import Optional




class ChangeIssueDTO(ChangeItemDTO):
    initiator: Optional[str] = None
