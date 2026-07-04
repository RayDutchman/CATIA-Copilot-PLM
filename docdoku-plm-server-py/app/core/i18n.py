import re
from pathlib import Path

SUPPORTED_LANGUAGES = ["fr", "en", "ru", "zh"]

_RESOURCE_DIR = Path(__file__).resolve().parent.parent / "resources" / "i18n"
_cache: dict[str, dict[str, str]] = {}

_LINE_RE = re.compile(r"^\s*([^#!=\s][^=]*?)\s*=\s*(.*)$")


def _resolve_lang(lang: str | None) -> str:
    if lang in ("fr", "ru", "zh"):
        return lang
    return "en"


def _load(lang: str) -> dict[str, str]:
    if lang in _cache:
        return _cache[lang]
    path = _RESOURCE_DIR / f"LocalStrings_{lang}.properties"
    table: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = _LINE_RE.match(line)
            if m:
                table[m.group(1)] = m.group(2)
    _cache[lang] = table
    return table


def get(key: str, lang: str | None = None, *args) -> str:
    table = _load(_resolve_lang(lang))
    template = table.get(key)
    if template is None:
        return key
    if args:
        try:
            return template.format(*args)
        except (IndexError, KeyError):
            return template
    return template
