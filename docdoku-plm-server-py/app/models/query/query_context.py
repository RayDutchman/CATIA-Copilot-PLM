"""QueryContext DTO。"""
from dataclasses import dataclass, field
@dataclass
class QueryContext: workspace_id: str = ""; user_login: str = ""; user_workspace_id: str = ""
