"""文件上传工具（对标 BinaryResourceUpload — multipart → vault + 错误响应）。"""
import logging
from pathlib import Path
from fastapi import UploadFile
from app.services import vault as vault_svc

_logger = logging.getLogger(__name__)


def save_upload_to_vault(upload: UploadFile, vault_path: Path) -> int:
    """将 UploadFile 内容写入 vault，返回写入字节数。"""
    data = upload.file.read()
    vault_svc.write_file(vault_path, data)
    return len(data)
