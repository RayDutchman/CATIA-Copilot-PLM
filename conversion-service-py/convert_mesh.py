#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_mesh.py — 基于 trimesh/ifcopenshell 的网格格式 → GLB 转换器

支持格式：STL / OFF / PLY / OBJ / DXF / DAE / IFC

依赖：
  trimesh>=4.4 (STL/OFF/PLY/OBJ/DXF/DAE)
  pycollada>=0.8 (DAE — trimesh 的 Collada loader)
  ifcopenshell>=0.8 (IFC)
  pygltflib>=1.16 (最终 GLB 封装，与 convert_step_glb.py 共用)

设计原则：
  - 所有支持格式都走同一 convert() 入口
  - 返回与 convert_step_glb.py 完全相同的 dict 结构：
    {"glb_path": str, "bbox": [...], "solid_count": int}
  - 无几何体时抛 ConversionError("no geometry generated from ...")
"""

import os
import sys
import numpy as np

__all__ = ["convert", "ConversionError", "SUPPORTED_EXTENSIONS"]

# 本模块支持的文件扩展名（小写，不含点）
# 注意：DXF 是 2D 格式，trimesh 以 Path2D 加载，无三角面几何体，不能转为 3D GLB。
SUPPORTED_EXTENSIONS = frozenset(["stl", "off", "ply", "obj", "dae", "ifc"])


class ConversionError(RuntimeError):
    """转换失败时抛出（与 convert_step_glb.py 的 ConversionError 命名一致）。"""
    pass


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

def convert(input_path: str, output_path: str, **kwargs) -> dict:
    """
    将网格格式文件转换为 GLB，供 main.py 编排层直接调用。

    参数:
        input_path  (str): 输入文件绝对路径（STL/OFF/PLY/OBJ/DXF/DAE/IFC）
        output_path (str): 输出 GLB 文件绝对路径
        **kwargs        : 占位参数（忽略，保持与 convert_step_glb.convert 签名兼容）

    返回:
        dict: {"glb_path": str, "bbox": [xmin,ymin,zmin,xmax,ymax,zmax], "solid_count": int}

    抛出:
        ConversionError: 文件不存在、格式不支持或无几何体时
    """
    if not os.path.exists(input_path):
        raise ConversionError(f"输入文件不存在: {input_path}")

    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ConversionError(f"不支持的格式: {ext}（支持：{sorted(SUPPORTED_EXTENSIONS)}）")

    if ext == "ifc":
        scene = _load_ifc(input_path)
    else:
        scene = _load_trimesh(input_path, ext)

    if scene is None or _is_empty(scene):
        raise ConversionError(f"no geometry generated from {input_path}")

    # 导出 GLB
    _export_glb(scene, output_path)

    # 计算包围盒
    bbox = _calc_bbox(scene)
    solid_count = _count_meshes(scene)

    return {
        "glb_path":    output_path,
        "bbox":        bbox,
        "solid_count": solid_count,
    }


# ---------------------------------------------------------------------------
# 内部：trimesh 加载
# ---------------------------------------------------------------------------

def _load_trimesh(input_path: str, ext: str):
    """用 trimesh 加载文件，返回 Scene 或 Trimesh。"""
    import trimesh

    try:
        result = trimesh.load(input_path, process=False, force="scene")
    except Exception as e:
        raise ConversionError(f"trimesh 加载失败 ({ext}): {e}") from e

    return result


# ---------------------------------------------------------------------------
# 内部：IFC 加载（ifcopenshell + trimesh）
# ---------------------------------------------------------------------------

def _load_ifc(input_path: str):
    """
    用 ifcopenshell 读取 IFC 文件，提取全部几何体，组装成 trimesh.Scene。
    """
    try:
        import ifcopenshell
        import ifcopenshell.geom
        import trimesh
    except ImportError as e:
        raise ConversionError(f"IFC 转换需要 ifcopenshell 库: {e}") from e

    try:
        ifc_file = ifcopenshell.open(input_path)
    except Exception as e:
        raise ConversionError(f"IFC 文件读取失败: {e}") from e

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    meshes = []
    iterator = ifcopenshell.geom.iterator(settings, ifc_file)
    if iterator.initialize():
        while True:
            shape = iterator.get()
            geo = shape.geometry
            verts = np.array(geo.verts, dtype=np.float32).reshape(-1, 3)
            faces = np.array(geo.faces, dtype=np.int32).reshape(-1, 3)
            if len(verts) > 0 and len(faces) > 0:
                mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
                meshes.append(mesh)
            if not iterator.next():
                break

    if not meshes:
        return None

    scene = trimesh.Scene()
    for i, m in enumerate(meshes):
        scene.add_geometry(m, node_name=f"ifc_mesh_{i}")
    return scene


# ---------------------------------------------------------------------------
# 内部：辅助函数
# ---------------------------------------------------------------------------

def _is_empty(scene) -> bool:
    """判断 scene 是否没有任何三角面。"""
    import trimesh
    if isinstance(scene, trimesh.Trimesh):
        return len(scene.faces) == 0
    if isinstance(scene, trimesh.Scene):
        return not any(
            isinstance(g, trimesh.Trimesh) and len(g.faces) > 0
            for g in scene.geometry.values()
        )
    return True


def _export_glb(scene, output_path: str) -> None:
    """将 scene 导出为 GLB 文件。"""
    import trimesh
    if isinstance(scene, trimesh.Trimesh):
        scene = trimesh.Scene(geometry={"mesh": scene})
    try:
        glb_bytes = scene.export(file_type="glb")
        with open(output_path, "wb") as f:
            f.write(glb_bytes)
    except Exception as e:
        raise ConversionError(f"GLB 导出失败: {e}") from e


def _calc_bbox(scene) -> list:
    """计算 scene 整体包围盒，返回 [xmin,ymin,zmin,xmax,ymax,zmax]。
    对 NaN/Inf 顶点做保护，返回退化的 [0,0,0,0,0,0]。"""
    import trimesh
    try:
        if isinstance(scene, trimesh.Trimesh):
            bounds = scene.bounds
        elif isinstance(scene, trimesh.Scene):
            all_bounds = [
                g.bounds for g in scene.geometry.values()
                if isinstance(g, trimesh.Trimesh) and len(g.faces) > 0
            ]
            if not all_bounds:
                return [0.0] * 6
            mins = np.min([b[0] for b in all_bounds], axis=0)
            maxs = np.max([b[1] for b in all_bounds], axis=0)
            bounds = np.array([mins, maxs])
        else:
            return [0.0] * 6
        # 保护 NaN/Inf（损坏文件的异常顶点）
        flat = bounds[0].tolist() + bounds[1].tolist()
        return [v if np.isfinite(v) else 0.0 for v in flat]
    except Exception:
        return [0.0] * 6


def _count_meshes(scene) -> int:
    """统计有效网格数量。"""
    import trimesh
    if isinstance(scene, trimesh.Trimesh):
        return 1 if len(scene.faces) > 0 else 0
    if isinstance(scene, trimesh.Scene):
        return sum(
            1 for g in scene.geometry.values()
            if isinstance(g, trimesh.Trimesh) and len(g.faces) > 0
        )
    return 0
