"""vault 文件存储服务。路径规则与 Payara FileStorageProvider 完全一致。"""
from pathlib import Path
from app.core.config import settings


def _vault_root() -> Path:
    return Path(settings.VAULT_PATH)


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
