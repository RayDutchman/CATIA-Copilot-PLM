"""RotationType 枚举 — 旋转表示方式。"""
from enum import Enum


class RotationType(str, Enum):
    ANGLE = "ANGLE"
    MATRIX = "MATRIX"
