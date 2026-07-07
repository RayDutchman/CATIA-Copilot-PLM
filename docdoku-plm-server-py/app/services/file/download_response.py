"""构建下载响应（对标 BinaryResourceDownloadResponseBuilder — Range + 缓存策略）。"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from fastapi.responses import Response

from app.services.file.binary_resource_streaming import parse_range_header
from app.services.file.download_meta import build_file_headers

_logger = logging.getLogger(__name__)


def prepare_download_response(
    data: bytes,
    file_path: Path,
    file_name: str,
    range_header: str | None = None,
    download_type: str | None = None,
    output_format: str | None = None,
    cache_max_age: int | None = 86400,
) -> Response:
    """构建文件下载 FastAPI Response（含 Range 支持 + 缓存头）。"""
    headers = build_file_headers(
        data, file_path, file_name,
        download_type=download_type, output_format=output_format,
        cache_max_age=cache_max_age,
    )
    if not range_header:
        headers["Content-Length"] = str(len(data))
        return Response(content=data, media_type=headers.pop("Content-Type"),
                        headers=headers)

    parsed = parse_range_header(range_header, len(data))
    if not parsed:
        return Response(status_code=416, content="Requested Range Not Satisfiable")

    start, end = parsed
    chunk = data[start:end + 1]
    headers["Content-Range"] = f"bytes {start}-{end}/{len(data)}"
    headers["Content-Length"] = str(len(chunk))
    return Response(
        content=chunk, status_code=206,
        media_type=headers.pop("Content-Type"),
        headers=headers,
    )


def download_error(message: str) -> Response:
    _logger.error("下载错误: %s", message)
    return Response(
        status_code=500,
        content=message,
        media_type="text/plain",
        headers={"Reason-Phrase": message},
    )
