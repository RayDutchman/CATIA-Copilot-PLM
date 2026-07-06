"""Query DTO。"""
from typing import List, Optional

class Query:
    def __init__(self, name: str = "", workspace_id: str = "", rules: Optional[List] = None):
        self.name = name; self.workspace_id = workspace_id; self.rules = rules or []
