#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
converter.py — 统一转换入口

暴露两个核心函数：
  convert_step(input, output, ...)  — STEP/IGES → GLB（基于 OpenCASCADE）
  convert_mesh(input, output, ...)  — STL/OFF/PLY/OBJ/DXF/DAE/IFC → GLB（基于 trimesh）
  convert(input, output, ...)       — 统一入口：按扩展名自动路由

并暴露 unaccent() 用于复现 Java Tools.unAccent() 的 vault 路径逻辑。
"""

import sys
import os
import unicodedata

# 将脚本所在目录加入 sys.path，以便 import convert_step_glb / convert_mesh 找到模块
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import convert_step_glb as _step_mod
import convert_mesh as _mesh_mod

# STEP/IGES 格式（OpenCASCADE 处理，颜色精确）
STEP_EXTENSIONS  = frozenset(["stp", "step", "igs", "iges"])
# 网格格式（trimesh/ifcopenshell 处理）
MESH_EXTENSIONS  = _mesh_mod.SUPPORTED_EXTENSIONS
# 全部支持的格式
ALL_EXTENSIONS   = STEP_EXTENSIONS | MESH_EXTENSIONS

# ConversionError — 优先使用 STEP 版（两者命名相同，取其一）
ConversionError = _step_mod.ConversionError


def convert_step(input_path: str, output_path: str, deflection: float = 0.05,
                 angular: float = 0.3) -> dict:
    """STEP/IGES → GLB（OpenCASCADE，支持颜色精确读取）"""
    return _step_mod.convert(input_path, output_path, deflection, angular)


def convert_mesh(input_path: str, output_path: str, **kwargs) -> dict:
    """STL/OFF/PLY/OBJ/DXF/DAE/IFC → GLB（trimesh/ifcopenshell）"""
    return _mesh_mod.convert(input_path, output_path)


def convert(input_path: str, output_path: str, **kwargs) -> dict:
    """
    统一入口：按文件扩展名自动路由到合适的转换器。

    返回: {"glb_path": str, "bbox": [...], "solid_count": int}
    抛出: ConversionError
    """
    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    if ext in STEP_EXTENSIONS:
        return convert_step(input_path, output_path,
                            kwargs.get("deflection", 0.05),
                            kwargs.get("angular", 0.3))
    if ext in MESH_EXTENSIONS:
        return convert_mesh(input_path, output_path)
    raise ConversionError(
        f"不支持的文件格式: .{ext}（支持：{sorted(ALL_EXTENSIONS)}）"
    )


__all__ = [
    "convert", "convert_step", "convert_mesh",
    "ConversionError", "unaccent",
    "ALL_EXTENSIONS", "STEP_EXTENSIONS", "MESH_EXTENSIONS",
]


def unaccent(text: str) -> str:
    """
    对齐 Java Tools.unAccent() 的修复后行为：
      1. NFD 规范化（分解组合字符）
      2. 删除所有 Mn 类别（Non-Spacing Mark，即变音符/组合符号）
      3. 不修改空格（Java 修复后的关键）

    示例：
        unaccent("Bevel Gear Formüla")  →  "Bevel Gear Formula"
        unaccent("O-Ring DIN 3771")     →  "O-Ring DIN 3771"   （空格保留）
        unaccent("A_B")                 →  "A_B"               （下划线保留）
    """
    nfd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")

