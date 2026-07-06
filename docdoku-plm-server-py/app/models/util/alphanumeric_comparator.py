"""AlphanumericComparator — 字符串自然排序。"""
import re

def alphanumeric_compare(a: str, b: str) -> int:
    """按自然顺序比较含数字的字符串（如 'part2' < 'part10'）。"""
    def _parts(s):
        return [(int(t) if t.isdigit() else t.lower()) for t in re.split(r"(\d+)", s)]
    pa, pb = _parts(a), _parts(b)
    if pa < pb: return -1
    if pa > pb: return 1
    return 0
