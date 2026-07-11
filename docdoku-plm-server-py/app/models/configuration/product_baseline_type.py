"""ProductBaselineType 枚举。"""
from enum import IntEnum

class ProductBaselineType(IntEnum):
    LATEST = 0
    RELEASED = 1
    EFFECTIVE_DATE = 2
    EFFECTIVE_SERIAL_NUMBER = 3
    EFFECTIVE_LOT_ID = 4
