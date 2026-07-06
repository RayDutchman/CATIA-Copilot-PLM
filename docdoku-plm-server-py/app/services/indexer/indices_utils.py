"""IndicesUtils——索引名称格式化工具。

对齐 Java IndicesUtils。
"""
import re
import unicodedata
from urllib.parse import quote

from app.services.indexer.indexer_mapping import INDEX_PREFIX, INDEX_SEPARATOR


def get_index_name(index_name: str, index_type: str) -> str:
    """构建完整的 ES 索引名。

    格式: {prefix}-{url_encoded_name}-{type}
    """
    encoded = format_index_name(index_name)
    return f"{INDEX_PREFIX}{INDEX_SEPARATOR}{encoded}{INDEX_SEPARATOR}{index_type}"


def format_index_name(name: str) -> str:
    """对索引名进行 URL 编码 + 去重音 + 小写化。"""
    name = name.strip().replace(" ", "-")
    name = unaccent(name)
    name = quote(name, safe="")
    return name.lower()


def format_doc_id(doc_id: str) -> str:
    """格式化 ES 文档 ID。"""
    return format_index_name(doc_id)


def unaccent(text: str) -> str:
    """移除 Unicode 重音符号（对齐 Java Tools.unAccent）。"""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))
