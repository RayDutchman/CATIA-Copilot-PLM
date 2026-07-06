"""QueryRule DTO。"""
from dataclasses import dataclass
@dataclass
class QueryRule: field: str = ""; type: str = ""; operator: str = ""; value: str = ""; id: str = ""
