"""文件下载工具（对标 FileDownloadTools — 文件名编码 + Content-Disposition）。

Already covered by app/services/file/download_meta.py — this is a re-export convenience module.
"""
from app.services.file.download_meta import (
    get_file_name,
    get_content_disposition,
    get_content_type,
    build_etag,
    build_file_headers,
)

__all__ = [
    "get_file_name",
    "get_content_disposition",
    "get_content_type",
    "build_etag",
    "build_file_headers",
]
