"""TagUserSubscription DTO。"""
from dataclasses import dataclass
@dataclass
class TagUserSubscription: tag: str = ""; user_login: str = ""
