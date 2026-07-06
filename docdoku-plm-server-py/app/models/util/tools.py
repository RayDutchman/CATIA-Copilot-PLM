"""Tools — 通用工具。"""
def str_to_bool(s: str) -> bool:
    return s.lower() in ("true", "1", "yes")
