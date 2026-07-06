"""ProvidedAccountKey 复合主键 — 对应 Java @IdClass。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProvidedAccountKey:
    provider_id: int
    sub: str
    account_login: str
