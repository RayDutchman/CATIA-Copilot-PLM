"""DateUtils — 日期工具。"""
from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc)
