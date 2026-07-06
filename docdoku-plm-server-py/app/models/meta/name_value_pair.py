"""NameValuePair DTO。"""
from dataclasses import dataclass
@dataclass
class NameValuePair:
    name: str; value: str
