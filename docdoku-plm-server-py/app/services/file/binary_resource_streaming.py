"""流式输出 BinaryResource（对标 BinaryResourceBinaryStreamingOutput + Range 支持）。

Func: stream_file_range(data, range_header) → bytes | None
"""
import logging
import re

_logger = logging.getLogger(__name__)


def parse_range_header(range_header: str, file_size: int) -> tuple[int, int] | None:
    """解析 HTTP Range 请求头，返回 (start, end) 或 None。"""
    if not range_header:
        return None
    m = re.match(r'^bytes=(\d+)-(\d*)$', range_header.strip())
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else file_size - 1
    if start > end or start >= file_size:
        return None
    return start, min(end, file_size - 1)


def stream_file_range(data: bytes, range_header: str) -> tuple[bytes, str] | None:
    """根据 Range 请求头对 data 切片，返回 (chunk, content_range_header) 或 None。"""
    parsed = parse_range_header(range_header, len(data))
    if not parsed:
        return None
    start, end = parsed
    chunk = data[start:end + 1]
    content_range = f"bytes {start}-{end}/{len(data)}"
    return chunk, content_range
