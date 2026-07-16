"""vault 文件存储服务。路径规则与 Payara FileStorageProvider 完全一致。"""
from pathlib import Path
from app.core.config import settings


def _vault_root() -> Path:
    return Path(settings.VAULT_PATH)


def workspace_vault_dir(workspace_id: str) -> Path:
    """Workspace 的 vault 根目录。"""
    return _vault_root() / workspace_id


def export_zip_base() -> Path:
    """导出的 zip 文件在 vault 中的存放根目录。"""
    return _vault_root()


def document_iteration_dir(
    workspace_id: str, document_id: str, version: str, iteration: int
) -> Path:
    """文档 Iteration 的 vault 物理目录。"""
    return (
        _vault_root() / workspace_id / "documents"
        / document_id / version / str(iteration)
    )


def document_template_attached_path(
    workspace_id: str, template_id: str, filename: str
) -> Path:
    """文档模板附件文件路径。"""
    return _vault_root() / workspace_id / "document-templates" / template_id / filename


def document_attached_path(
    workspace_id: str, document_id: str, version: str,
    iteration: int, filename: str
) -> Path:
    """文档附件文件路径。"""
    return (
        _vault_root() / workspace_id / "documents"
        / document_id / version / str(iteration) / filename
    )


def document_attached_fullname(
    workspace_id: str, document_id: str, version: str,
    iteration: int, filename: str
) -> str:
    """文档附件文件的 full_name。"""
    return f"{workspace_id}/documents/{document_id}/{version}/{iteration}/{filename}"


def part_iteration_dir(
    workspace_id: str, part_number: str, version: str, iteration: int
) -> Path:
    """零件 Iteration 的 vault 物理目录。"""
    return (
        _vault_root() / workspace_id / "parts"
        / part_number / version / str(iteration)
    )


def part_nativecad_path(
    workspace_id: str, part_number: str, version: str,
    iteration: int, filename: str
) -> Path:
    """原生 CAD 文件路径（STEP 等）。"""
    return (
        _vault_root() / workspace_id / "parts"
        / part_number / version / str(iteration)
        / "nativecad" / filename
    )


def part_nativecad_fullname(
    workspace_id: str, part_number: str, version: str,
    iteration: int, filename: str
) -> str:
    """原生 CAD 文件的 full_name。"""
    return f"{workspace_id}/parts/{part_number}/{version}/{iteration}/nativecad/{filename}"


def part_geometry_path(
    workspace_id: str, part_number: str, version: str,
    iteration: int, quality: str
) -> Path:
    """几何体 GLB 文件路径。对齐 Java：无 geometry 子目录。"""
    return (
        _vault_root() / workspace_id / "parts"
        / part_number / version / str(iteration)
        / f"{quality}.glb"
    )


def part_geometry_fullname(
    workspace_id: str, part_number: str, version: str,
    iteration: int, quality: str
) -> str:
    """几何体 GLB 文件的 full_name。"""
    return f"{workspace_id}/parts/{part_number}/{version}/{iteration}/{quality}.glb"


def part_attached_path(
    workspace_id: str, part_number: str, version: str,
    iteration: int, filename: str
) -> Path:
    """附件文件路径（PDF 图纸、CATPart 等）。"""
    return (
        _vault_root() / workspace_id / "parts"
        / part_number / version / str(iteration)
        / "attachedfiles" / filename
    )


def part_attached_fullname(
    workspace_id: str, part_number: str, version: str,
    iteration: int, filename: str
) -> str:
    """零件附件文件的 full_name。"""
    return f"{workspace_id}/parts/{part_number}/{version}/{iteration}/attachedfiles/{filename}"


def resolve(full_name: str) -> Path:
    """将给定的 full_name 转换为绝对路径对象。替代原本外部的 vault_svc._vault_root() / full_name 拼接行为。"""
    return _vault_root() / full_name


def _template_base(workspace_id: str, template_id: str) -> Path:
    return _vault_root() / workspace_id / "part-templates" / template_id


def template_attached_path(workspace_id: str, template_id: str,
                            filename: str) -> Path:
    """零件模板附件磁盘路径。"""
    return _template_base(workspace_id, template_id) / filename


def template_attached_fullname(workspace_id: str, template_id: str,
                                filename: str) -> str:
    """零件模板附件的 full_name（对齐 BinaryResource.full_name 格式）。"""
    return f"{workspace_id}/part-templates/{template_id}/{filename}"


def product_instance_iteration_path(
    workspace_id: str, serial_number: str,
    iteration: int, filename: str
) -> Path:
    """产品实例 Iteration 文件路径。"""
    return (
        _vault_root() / workspace_id / "product-instances" / serial_number
        / "iterations" / str(iteration) / filename
    )


def product_instance_iteration_fullname(
    workspace_id: str, serial_number: str,
    iteration: int, filename: str
) -> str:
    """产品实例 Iteration 文件的 full_name。"""
    return f"{workspace_id}/product-instances/{serial_number}/iterations/{iteration}/{filename}"


def product_instance_path(
    workspace_id: str, serial_number: str, path_data_id: str,
    iteration: int, filename: str
) -> Path:
    """产品实例 PathData 文件路径。"""
    return (
        _vault_root() / workspace_id / "product-instances" / serial_number
        / "pathdata" / path_data_id / "iterations" / str(iteration) / filename
    )


def product_instance_fullname(
    workspace_id: str, serial_number: str, path_data_id: str,
    iteration: int, filename: str
) -> str:
    """产品实例 PathData 文件的 full_name。"""
    return f"{workspace_id}/product-instances/{serial_number}/pathdata/{path_data_id}/iterations/{iteration}/{filename}"


def read_file(path: Path) -> bytes:
    """读取 vault 文件内容。文件不存在时抛出 FileNotFoundError。"""
    return path.read_bytes()


def write_file(path: Path, data: bytes) -> None:
    """写入 vault 文件，自动创建父目录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def move_file(old_path: Path, new_path: Path) -> None:
    """移动/重命名 vault 文件。源文件不存在时不报错（幂等）。"""
    if old_path.exists():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.rename(new_path)
