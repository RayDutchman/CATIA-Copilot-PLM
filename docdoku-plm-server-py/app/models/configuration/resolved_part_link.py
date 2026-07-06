"""ResolvedPartLink DTO。"""
from dataclasses import dataclass

@dataclass
class ResolvedPartLink:
    part_link_id: int
    source_part_key: str
    target_part_key: str
    path: list
