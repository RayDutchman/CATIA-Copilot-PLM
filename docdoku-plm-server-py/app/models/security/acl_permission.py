"""ACLPermission 枚举。"""
from enum import IntEnum

class ACLPermission(IntEnum):
    FORBIDDEN = 0
    READ_ONLY = 1
    FULL_ACCESS = 2
