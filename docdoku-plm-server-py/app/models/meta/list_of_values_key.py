"""ListOfValuesKey 复合主键。"""
from dataclasses import dataclass
@dataclass(frozen=True)
class ListOfValuesKey:
    workspace_id: str; name: str
