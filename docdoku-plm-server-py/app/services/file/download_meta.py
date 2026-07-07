"""文件下载元数据（对标 BinaryResourceDownloadMeta — MIME 类型 + ETag + Content-Disposition）。"""
from datetime import datetime, timezone
from pathlib import Path

CHARSET = "UTF-8"

_MIME_MAP: dict[str, str] = {
    "pdf": "application/pdf",
    "doc": "application/msword", "dot": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint", "pot": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "csv": "text/csv",
    "txt": "text/plain",
    "html": "text/html", "htm": "text/html",
    "xml": "text/xml",
    "json": "application/json",
    "js": "application/javascript",
    "css": "text/css",
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "jpe": "image/jpeg",
    "png": "image/png", "gif": "image/gif", "bmp": "image/bmp",
    "svg": "image/svg+xml",
    "mp3": "audio/mpeg",
    "mp4": "video/mp4",
    "avi": "video/x-msvideo",
    "mov": "video/quicktime", "qt": "video/quicktime",
    "mpeg": "video/mpeg", "mpg": "video/mpeg",
    "ogg": "video/ogg",
    "zip": "application/zip", "rar": "application/x-rar-compressed",
    "stp": "application/step", "step": "application/step",
    "glb": "model/gltf-binary",
    "stl": "model/stl",
    "obj": "model/obj",
}


def get_content_type(full_name: str, output_format: str | None = None) -> str:
    """根据文件扩展名获取 MIME 类型。"""
    name = full_name
    name_suffix = full_name
    if output_format:
        name_suffix += "." + output_format
    ext = Path(name_suffix).suffix.lstrip(".").lower()
    content_type = _MIME_MAP.get(ext, "application/octet-stream")
    if content_type.startswith("text"):
        content_type += f";charset={CHARSET}"
    return content_type


def get_content_disposition(download_type: str | None, file_name: str) -> str:
    """生成 Content-Disposition 响应头。"""
    disposition = "inline" if download_type == "viewer" else "attachment"
    return f'{disposition}; filename="{file_name}"; filename*="{file_name}"'


def get_file_name(full_name: str, output_format: str | None = None) -> str:
    """生成下载文件名（含 URL 编码处理）。"""
    from urllib.parse import quote
    try:
        fn = quote(full_name, safe="")
    except Exception:
        fn = full_name
    if output_format:
        fn += "." + output_format
    return fn


def build_etag(full_name: str, length: int, last_modified: datetime | None = None) -> str:
    """生成 ETag。"""
    lm = int(last_modified.timestamp()) if last_modified else 0
    return f'"{full_name}_{length}_{lm}"'


def build_file_headers(data: bytes, file_path: Path, file_name: str,
                       download_type: str | None = None,
                       output_format: str | None = None,
                       cache_max_age: int | None = 86400) -> dict:
    """构建完整的文件下载响应头字典。"""
    headers: dict = {}
    try:
        stat = file_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    except (FileNotFoundError, OSError):
        mtime = datetime.now(tz=timezone.utc)

    headers["Content-Disposition"] = get_content_disposition(download_type, file_name)
    headers["Content-Type"] = get_content_type(file_name, output_format)
    headers["Last-Modified"] = mtime.strftime("%a, %d %b %Y %H:%M:%S GMT")
    headers["ETag"] = build_etag(file_name, len(data), mtime)

    if cache_max_age is not None:
        headers["Cache-Control"] = f"max-age={cache_max_age}"
    else:
        headers["Cache-Control"] = "no-cache"

    return headers
