"""开发用错误收集器。

记录所有 4xx/5xx 请求（URL、方法、请求体、响应体、状态码、时间戳），
通过 /dev/errors 端点暴露，方便调试前端问题。
"""
import time
import json
from collections import deque
from typing import Optional

# 内存中最多保留 500 条，循环覆盖
_MAX = 500
_errors: deque = deque(maxlen=_MAX)


def record(
    method: str,
    url: str,
    status: int,
    req_body: Optional[str],
    res_body: Optional[str],
    user: Optional[str] = None,
):
    """记录一条错误请求。"""
    _errors.appendleft({
        "ts": time.strftime("%H:%M:%S"),
        "method": method,
        "url": url,
        "status": status,
        "user": user or "",
        "req": _truncate(req_body),
        "res": _truncate(res_body),
    })


def get_errors(limit: int = 100, min_status: int = 400) -> list:
    """返回最近的错误记录，按时间倒序。"""
    return [e for e in _errors if e["status"] >= min_status][:limit]


def clear():
    _errors.clear()


def _truncate(s: Optional[str], maxlen: int = 1000) -> Optional[str]:
    if s is None:
        return None
    if len(s) > maxlen:
        return s[:maxlen] + f"…（共 {len(s)} 字符）"
    return s
