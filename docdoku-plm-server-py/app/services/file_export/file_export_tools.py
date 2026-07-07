"""文件导出工具（对标 FileExportTools — Stream→ZIP 辅助）。"""
import io
import zipfile
import logging

_logger = logging.getLogger(__name__)


def add_to_zip_file(
    binary_data: bytes,
    binary_name: str,
    folder_name: str,
    zos: zipfile.ZipFile,
) -> None:
    """将字节数据写入 ZIP 文件中的指定目录下。"""
    arcname = f"{folder_name}/{binary_name}"
    try:
        zos.writestr(arcname, binary_data)
    except Exception:
        _logger.warning("无法将文件添加到 ZIP: %s", arcname)


class ZipStream:
    """内存中构建 ZIP 文件的上下文管理器。

    使用方式:
        with ZipStream() as zs:
            add_to_zip_file(data, "file.pdf", "folder", zs)
            bytes_io = zs.getvalue()
    """

    def __init__(self):
        self._buffer = io.BytesIO()
        self._zip: zipfile.ZipFile | None = None

    def __enter__(self) -> zipfile.ZipFile:
        self._zip = zipfile.ZipFile(self._buffer, "w", zipfile.ZIP_DEFLATED)
        return self._zip

    def __exit__(self, *args):
        if self._zip:
            self._zip.close()

    def getvalue(self) -> bytes:
        return self._buffer.getvalue()
