"""转换器工具函数（对标 ConverterUtils）。"""
import logging
from pathlib import Path

_logger = logging.getLogger(__name__)

# 支持的 CAD 格式
CAD_EXTENSIONS: set[str] = {
    "stp", "step", "igs", "iges", "stl", "off", "ply", "obj", "dae", "ifc",
}
# 可转换为 GLB 的格式
GEOMETRY_CAPABLE: set[str] = {"stp", "step", "igs", "iges", "stl", "obj"}


def is_cad_file(filename: str) -> bool:
    """判断文件名是否为 CAD 文件。"""
    ext = Path(filename).suffix.lstrip(".").lower()
    return ext in CAD_EXTENSIONS


def is_geometry_capable(filename: str) -> bool:
    """判断文件是否可转换为 3D 几何体（GLB）。"""
    ext = Path(filename).suffix.lstrip(".").lower()
    return ext in GEOMETRY_CAPABLE


def vault_nativecad_path(ws: str, pn: str, ver: str, iteration: int, filename: str) -> str:
    """构建 nativecad 文件的 vault 相对路径。"""
    return f"{ws}/parts/{pn}/{ver}/{iteration}/nativecad/{filename}"
