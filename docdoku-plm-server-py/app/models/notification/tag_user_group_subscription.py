"""TagUserGroupSubscription DTO。"""
from dataclasses import dataclass
@dataclass
class TagUserGroupSubscription: tag: str = ""; group_id: str = ""
