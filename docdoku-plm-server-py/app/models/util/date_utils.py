"""DateUtils — 日期工具。"""
from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_iso_date(d: datetime | None) -> str | None:
    """将 datetime 格式化为 ISO-8601 风格字符串，3 位毫秒 + Z 后缀。

    示例: "2024-01-15T08:30:45.123Z"
    """
    if d is None:
        return None
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"
