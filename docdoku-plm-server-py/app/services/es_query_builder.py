"""ES 搜索查询构建——对标 Payara IndexerQueryBuilder + SearchQueryParser。

ES field key 全部来自 IndexerMapping.java 常量。
"""
import logging

from elasticsearch import ConnectionError, ConnectionTimeout

from app.services.indexer_manager import indexer_manager as _im

logger = logging.getLogger(__name__)

_FUZZINESS = "AUTO"


class EsQueryBuilder:
    """ES bool query DSL 构建器。"""

    # ── 零件搜索 ──────────────────────────────────────────────

    def search_parts(self, ws: str, params: dict) -> list:
        """返回匹配的 partKey 列表（格式: '{number}-{version}-{iteration}'）。"""
        try:
            idx = _im._part_index(ws)
            must = self._build_part_must(params)
            body = {"query": {"bool": {"must": must}}} if must else {"query": {"match_all": {}}}
            body["from"] = params.get("from", 0)
            body["size"] = params.get("size", 20)
            result = _im.es.search(index=idx, body=body, _source=False)
            return [h["_id"] for h in result["hits"]["hits"]]
        except (ConnectionError, ConnectionTimeout, Exception):
            logger.warning("ES search_parts failed for workspace %s", ws, exc_info=True)
            return []

    def _build_part_must(self, params: dict) -> list:
        must = []
        # partNumber → match（精确，无 fuzziness）── IndexerQueryBuilder:1551
        n = params.get("number")
        if n:
            must.append({"match": {"partNumber": n}})
        # partName → match（fuzziness=AUTO）── IndexerQueryBuilder:1554
        nm = params.get("name")
        if nm:
            must.append({"match": {"partName": {"query": nm, "fuzziness": _FUZZINESS}}})
        # queryString → bool should（元数据 OR 文件内容）── SearchQueryParser
        q = params.get("q")
        if q:
            must.append({"bool": {"should": [
                {"query_string": {"query": q, "default_operator": "AND"}},
                {"nested": {"path": "files", "query": {"match": {"files.content": q}}, "score_mode": "none"}},
            ]}})
        must.extend(self._build_common_must(params))
        return must

    # ── 文档搜索 ──────────────────────────────────────────────

    def search_documents(self, ws: str, params: dict) -> list:
        """返回匹配的 docKey 列表（格式: '{docMId}-{version}-{iteration}'）。"""
        try:
            idx = _im._doc_index(ws)
            must = self._build_doc_must(params)
            body = {"query": {"bool": {"must": must}}} if must else {"query": {"match_all": {}}}
            body["from"] = params.get("from", 0)
            body["size"] = params.get("size", 20)
            result = _im.es.search(index=idx, body=body, _source=False)
            return [h["_id"] for h in result["hits"]["hits"]]
        except (ConnectionError, ConnectionTimeout, Exception):
            logger.warning("ES search_documents failed for workspace %s", ws, exc_info=True)
            return []

    def _build_doc_must(self, params: dict) -> list:
        must = []
        # docMId → match ── IndexerQueryBuilder:1528
        did = params.get("id")
        if did:
            must.append({"match": {"docMId": did}})
        # title → match（fuzziness=AUTO）── IndexerQueryBuilder:1532
        t = params.get("title")
        if t:
            must.append({"match": {"title": {"query": t, "fuzziness": _FUZZINESS}}})
        # folder → match + fuzziness ── IndexerQueryBuilder:1535
        f = params.get("folder")
        if f:
            must.append({"match": {"folder": {"query": f, "fuzziness": _FUZZINESS}}})
        # queryString → bool should（元数据 OR 文件内容）── SearchQueryParser
        q = params.get("q")
        if q:
            must.append({"bool": {"should": [
                {"query_string": {"query": q, "default_operator": "AND"}},
                {"nested": {"path": "files", "query": {"match": {"files.content": q}}, "score_mode": "none"}},
            ]}})
        must.extend(self._build_common_must(params))

        return must

    def _build_attribute_queries(self, attr_string: str) -> list:
        """解析 attributes 参数并构建 nested queries。对齐 IndexerQueryBuilder.addAttributeToQueries。
        格式: 'TYPE:name:value[;TYPE:name:value]'，类型可以是 TEXT/BOOLEAN/DATE/NUMBER/URL/LOV。
        同名字段的值之间是 OR（should），不同名字段之间是 AND（must）。
        """
        attr_queries = []

        # 1. 解析: 按名分组 → {name: [values]}
        groups = {}
        for raw in attr_string.split(";"):
            raw = raw.strip()
            if not raw:
                continue
            parts = raw.split(":", 2)
            if len(parts) < 3:
                continue
            attr_type, name, value = parts[0].strip(), parts[1].strip(), parts[2].strip()
            groups.setdefault(name, []).append(value)

        # 2. 为每种属性名构建 nested query
        for ns_name, values in groups.items():
            name_query = {"nested": {
                "path": "attributes",
                "query": {"term": {"attributes.attr_name": ns_name}},
            }}
            if len(values) == 1:
                value_query = {"nested": {
                    "path": "attributes",
                    "query": {"bool": {"must": [
                        {"term": {"attributes.attr_name": ns_name}},
                        {"term": {"attributes.attr_value": values[0]}},
                    ]}},
                }}
                attr_queries.append(value_query)
            else:
                bool_q = {"bool": {"should": [], "must_not": []}}
                for v in values:
                    bool_q["bool"]["should"].append(
                        {"nested": {
                            "path": "attributes",
                            "query": {"bool": {"must": [
                                {"term": {"attributes.attr_name": ns_name}},
                                {"term": {"attributes.attr_value": v}},
                            ]}},
                        }}
                    )
                bool_q["bool"]["must_not"].append(
                    {"nested": {
                        "path": "attributes",
                        "query": {"term": {"attributes.attr_value": ""}},
                    }}
                )
                attr_queries.append(bool_q)

        return attr_queries

    # ── 公共查询条件 ──────────────────────────────────────────

    def _build_common_must(self, params: dict) -> list:
        must = []
        # version → term ── IndexerQueryBuilder:1572
        v = params.get("version")
        if v:
            must.append({"term": {"version": v}})
        # author → bool should on authorName + authorLogin ── IndexerQueryBuilder:1575-1579
        a = params.get("author")
        if a:
            must.append({"bool": {"should": [
                {"match": {"authorName": {"query": a, "fuzziness": _FUZZINESS}}},
                {"match": {"authorLogin": {"query": a, "fuzziness": _FUZZINESS}}},
            ]}})
        # type → match（fuzziness=AUTO）── IndexerQueryBuilder:1582
        tp = params.get("type")
        if tp:
            must.append({"match": {"type": {"query": tp, "fuzziness": _FUZZINESS}}})
        # creationDate range ── IndexerQueryBuilder:1585-1591
        cf = params.get("createdFrom")
        if cf:
            must.append({"range": {"creationDate": {"gte": _to_es_date(cf)}}})
        ct = params.get("createdTo")
        if ct:
            must.append({"range": {"creationDate": {"lte": _to_es_date(ct)}}})
        # modificationDate range ── IndexerQueryBuilder:1593-1599
        mf = params.get("modifiedFrom")
        if mf:
            must.append({"range": {"modificationDate": {"gte": _to_es_date(mf)}}})
        mt = params.get("modifiedTo")
        if mt:
            must.append({"range": {"modificationDate": {"lte": _to_es_date(mt)}}})
        # tags → terms ── IndexerQueryBuilder:1605-1606
        tags = params.get("tags")
        if tags:
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            if tags:
                must.append({"terms": {"tags": tags}})
        # content → nested files.content ── IndexerQueryBuilder:1601-1602
        content = params.get("content")
        if content:
            must.append({"nested": {
                "path": "files",
                "query": {"match": {"files.content": content}},
                "score_mode": "avg",
            }})
        # attributes → nested query ── IndexerQueryBuilder:242-278
        attrs = params.get("attributes")
        if attrs:
            if isinstance(attrs, str):
                must.extend(self._build_attribute_queries(attrs))
            elif isinstance(attrs, list):
                must.extend(attrs)
        return must

    def ping(self) -> bool:
        """检测 ES 是否可用，透传到 _im.es.ping()。"""
        try:
            return _im.es.ping()
        except Exception:
            logger.warning("ES ping failed", exc_info=True)
            return False


es_query_builder = EsQueryBuilder()


# ── helpers ─────────────────────────────────────────────────────

def bool_string(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("true", "1", "yes")
    return bool(v)


def _to_es_date(v) -> str:
    """确保日期值为 ISO 字符串。"""
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)
