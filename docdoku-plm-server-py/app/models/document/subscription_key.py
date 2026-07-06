"""SubscriptionKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class SubscriptionKey:
    subscriber_login: str; subscriber_workspace_id: str
