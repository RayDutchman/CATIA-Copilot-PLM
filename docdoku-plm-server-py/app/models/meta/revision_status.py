"""RevisionStatus 枚举。"""
from enum import IntEnum

class RevisionStatus(IntEnum):
    WIP = 0
    RELEASED = 1
    OBSOLETE = 2
