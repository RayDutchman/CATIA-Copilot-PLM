"""NamingConvention — 命名约定。"""
import re

def is_valid_name(name: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9_\-\.]+$', name))
