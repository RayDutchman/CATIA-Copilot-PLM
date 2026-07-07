"""搜索查询参数解析器（对标 SearchQueryParser — REST 参数 → PartSearchQuery / DocumentSearchQuery dict）。"""
import re
import logging
from datetime import datetime
from urllib.parse import unquote

_logger = logging.getLogger(__name__)

_ATTR_DELIMITER_REGEX = re.compile(r"(?<!\\);")
_ATTR_SPLITTER_REGEX = re.compile(r"(?<!\\):")


def _parse_date(value: str) -> datetime | None:
    try:
        v = value.strip()
        v = v.replace("Z", "+00:00")
        return datetime.fromisoformat(v)
    except (ValueError, TypeError):
        return None


def _parse_attributes(value: str) -> list[dict]:
    """解析属性查询字符串: type:name:value;type:name:value"""
    result: list[dict] = []
    parts = _ATTR_DELIMITER_REGEX.split(value)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        first_colon = part.index(":")
        attr_type = part[:first_colon].upper()
        rest = part[first_colon + 1:]

        match = _ATTR_SPLITTER_REGEX.search(rest)
        if not match:
            _logger.warning("无法解析属性查询: %s", part)
            continue
        second_colon = match.start()
        attr_name = rest[:second_colon]
        attr_value = rest[second_colon + 1:]

        entry: dict = {"type": attr_type, "name": attr_name, "value": attr_value}
        if attr_type == "BOOLEAN":
            entry["value"] = attr_value.lower() in ("true", "1", "yes")
        elif attr_type == "NUMBER":
            try:
                entry["value"] = float(attr_value)
            except (ValueError, TypeError):
                _logger.warning("无法解析数字属性: %s", attr_value)
                continue
        elif attr_type == "DATE":
            dt = _parse_date(attr_value)
            if dt is None:
                continue
            entry["value"] = dt

        result.append(entry)
    return result


def parse_document_query(workspace_id: str, params: dict[str, str]) -> dict:
    """将 REST 查询参数解析为文档搜索查询字典。"""
    result: dict = {
        "workspaceId": workspace_id,
        "q": params.get("q"),
        "id": params.get("id"),
        "title": params.get("title"),
        "version": params.get("version"),
        "author": params.get("author"),
        "type": params.get("type"),
        "folder": params.get("folder"),
        "createdFrom": _parse_date(params.get("createdFrom", "")),
        "createdTo": _parse_date(params.get("createdTo", "")),
        "modifiedFrom": _parse_date(params.get("modifiedFrom", "")),
        "modifiedTo": _parse_date(params.get("modifiedTo", "")),
        "tags": params.get("tags", "").split(",") if params.get("tags") else [],
        "content": params.get("content"),
        "attributes": _parse_attributes(params.get("attributes", "")),
        "fetchHeadOnly": params.get("fetchHeadOnly", "false").lower() == "true",
    }
    return {k: v for k, v in result.items() if v is not None and v != []}


def parse_part_query(workspace_id: str, params: dict[str, str]) -> dict:
    """将 REST 查询参数解析为零件搜索查询字典。"""
    result: dict = {
        "workspaceId": workspace_id,
        "q": params.get("q"),
        "number": params.get("number"),
        "name": params.get("name"),
        "version": params.get("version"),
        "author": params.get("author"),
        "type": params.get("type"),
        "createdFrom": _parse_date(params.get("createdFrom", "")),
        "createdTo": _parse_date(params.get("createdTo", "")),
        "modifiedFrom": _parse_date(params.get("modifiedFrom", "")),
        "modifiedTo": _parse_date(params.get("modifiedTo", "")),
        "tags": params.get("tags", "").split(",") if params.get("tags") else [],
        "standardPart": (
            params.get("standardPart", "false").lower() == "true"
            if "standardPart" in params else None
        ),
        "content": params.get("content"),
        "attributes": _parse_attributes(params.get("attributes", "")),
        "fetchHeadOnly": params.get("fetchHeadOnly", "false").lower() == "true",
    }
    return {k: v for k, v in result.items() if v is not None and v != []}
