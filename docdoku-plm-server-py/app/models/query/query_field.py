"""QueryField DTO。"""
from dataclasses import dataclass
@dataclass
class QueryField: field_name: str = ""; field_label: str = ""
