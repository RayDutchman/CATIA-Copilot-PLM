"""Version 值对象 — 版本号递增逻辑。"""
from dataclasses import dataclass, field
from typing import List


_VERSION_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class VersionFormatError(ValueError):
    pass


@dataclass
class Version:
    _units: List[int] = field(default_factory=lambda: [0])

    def __init__(self, value: str = "A"):
        self._units = []
        for ch in value.upper():
            idx = _VERSION_CHARS.find(ch)
            if idx < 0:
                raise VersionFormatError(f"Invalid version character: {ch}")
            self._units.append(idx)

    def increase(self) -> None:
        """递增版本号：A→B, ..., Z→AA, AZ→BA。"""
        i = len(self._units) - 1
        while i >= 0:
            self._units[i] += 1
            if self._units[i] < 26:
                return
            self._units[i] = 0
            i -= 1
        self._units.insert(0, 0)

    def __str__(self) -> str:
        return "".join(_VERSION_CHARS[i] for i in self._units)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Version):
            return False
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))

    def __lt__(self, other: "Version") -> bool:
        return str(self) < str(other)
