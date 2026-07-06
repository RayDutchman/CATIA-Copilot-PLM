"""RotationMatrix 嵌入式值对象 — 3x3 旋转矩阵。"""
from dataclasses import dataclass


@dataclass
class RotationMatrix:
    m00: float = 1.0; m01: float = 0.0; m02: float = 0.0
    m10: float = 0.0; m11: float = 1.0; m12: float = 0.0
    m20: float = 0.0; m21: float = 0.0; m22: float = 1.0
