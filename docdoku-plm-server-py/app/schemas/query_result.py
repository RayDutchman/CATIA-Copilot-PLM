"""QueryResult 序列化（对齐 Payara QueryResultMessageBodyWriter.generateJSONResponse）。

将查询结果行（PartRevision + 可选 PBS 上下文）按 query.selects 序列化为 JSON 行数组。
- pr.partKey 恒输出
- pm.* / pr.* / author.* / ctx.* 输出标量
- attr-* / pd-attr-* 始终输出为数组
"""
from datetime import datetime

from sqlalchemy import text

# dtype(JPA 判别符) → InstanceAttributeType 枚举名（对齐 product_structure._DTYPE_TO_TYPE）
_DTYPE_TO_TYPE = {
    "InstanceTextAttribute": "TEXT",
    "InstanceNumberAttribute": "NUMBER",
    "InstanceDateAttribute": "DATE",
    "InstanceBooleanAttribute": "BOOLEAN",
    "InstanceURLAttribute": "URL",
    "InstanceListOfValuesAttribute": "LOV",
    "InstanceLongTextAttribute": "LONG_TEXT",
    "InstancePartNumberAttribute": "PART_NUMBER",
}


def _iso(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat() + "Z"
    return str(dt)


def _last_checked_in_iteration(pr):
    """返回最后一个已检入迭代（对齐 getLastCheckedInIteration），无则返回末迭代。"""
    iters = pr.iterations or []
    checked_in = [it for it in iters if it.check_in_date is not None]
    if checked_in:
        return max(checked_in, key=lambda x: x.iteration)
    return iters[-1] if iters else None


def _account_name(db, login):
    if db is None or not login:
        return None
    row = db.execute(text("SELECT name FROM account WHERE login = :l"),
                     {"l": login}).first()
    return row[0] if row else None


def _load_part_attrs(db, ws, pn, ver, it):
    """加载零件迭代实例属性 → {f"attr-{TYPE}.{name}": [值,...]}（多值合并）。"""
    if it is None:
        return {}
    rows = db.execute(text(
        "SELECT ia.dtype, ia.name, ia.textvalue, ia.numbervalue, ia.datevalue, "
        "ia.booleanvalue, ia.urlvalue, ia.longtextvalue, ia.indexvalue, ia.partmaster_partnumber "
        "FROM instanceattribute ia "
        "JOIN partiteration_attribute pia ON pia.instanceattribute_id = ia.id "
        "WHERE pia.workspace_id=:ws AND pia.partmaster_partnumber=:pn "
        "AND pia.partrevision_version=:ver AND pia.iteration=:it "
        "ORDER BY pia.attribute_order"
    ), {"ws": ws, "pn": pn, "ver": ver, "it": it}).fetchall()
    result = {}
    for r in rows:
        attr_type = _DTYPE_TO_TYPE.get(r[0] or "InstanceTextAttribute", "TEXT")
        if attr_type in ("TEXT",):
            value = r[2]
        elif attr_type == "NUMBER":
            value = str(r[3]) if r[3] is not None else None
        elif attr_type == "DATE":
            value = _iso(r[4])
        elif attr_type == "BOOLEAN":
            value = str(r[5]) if r[5] is not None else None
        elif attr_type == "URL":
            value = r[6]
        elif attr_type == "LONG_TEXT":
            value = r[7]
        elif attr_type == "LOV":
            value = str(r[8]) if r[8] is not None else None
        elif attr_type == "PART_NUMBER":
            value = r[9]
        else:
            value = r[2]
        key = f"attr-{attr_type}.{r[1] or ''}"
        result.setdefault(key, []).append(value if value is not None else "")
    return result


def _join_p2p(links):
    """把 P2P sources/targets（{type: [paths]}）拼为字符串。"""
    if not links:
        return ""
    parts = []
    for link_type, paths in links.items():
        for p in paths:
            parts.append(f"{link_type}:{p}")
    return ",".join(parts)


def _select_value(s, pr, master, it, row, db, attrs, pd_attrs):
    """按 select 字段名取值，返回 None 表示不输出该键。"""
    if s.startswith("attr-"):
        return attrs.get(s, [])
    if s.startswith("pd-attr-"):
        return pd_attrs.get(s, [])
    if s == "pm.number":
        return pr.partmaster_partnumber
    if s == "pm.name":
        return (master.name if master else "") or ""
    if s == "pm.type":
        return (master.type if master else "") or ""
    if s == "pm.standardPart":
        return bool(master.standard_part) if master else False
    if s == "pr.version":
        return pr.version
    if s == "pr.status":
        return pr.status_label
    if s == "pr.creationDate":
        return _iso(pr.creation_date)
    if s == "pr.modificationDate":
        return _iso(it.modification_date) if it else None
    if s == "pr.checkInDate":
        return _iso(it.check_in_date) if it else None
    if s == "pr.checkOutDate":
        return _iso(pr.check_out_date)
    if s in ("pr.lifeCycleState", "pr.linkedDocuments"):
        return ""
    if s == "author.login":
        return pr.author_login
    if s == "author.name":
        return _account_name(db, pr.author_login) or pr.author_login
    if s.startswith("ctx."):
        ctx = row.get("context")
        if ctx is None:
            return None
        if s == "ctx.depth":
            return row.get("depth", 0)
        if s == "ctx.productId":
            return ctx.get("configurationItemId")
        if s == "ctx.serialNumber":
            return ctx.get("serialNumber")
        if s == "ctx.amount":
            return str(row.get("amount", ""))
        if s == "ctx.p2p.source":
            return _join_p2p(row.get("sources"))
        if s == "ctx.p2p.target":
            return _join_p2p(row.get("targets"))
    return None


def build_query_result_rows(rows, query, db):
    """将查询结果行序列化为 JSON 行数组（按 query.selects 选择列）。

    rows: list[dict]，每项至少含 "partRevision"(PartRevision ORM)，
          PBS 行另含 context/depth/amount/sources/targets/pathDataAttrs。
    """
    selects = query.get("selects") or []
    need_attr = any(s.startswith("attr-") for s in selects)
    out_rows = []
    for row in rows:
        pr = row["partRevision"]
        master = pr.part_master
        it = _last_checked_in_iteration(pr)
        d = {"pr.partKey": f"{pr.partmaster_partnumber}-{pr.version}"}
        attrs = {}
        if need_attr and db is not None:
            attrs = _load_part_attrs(
                db, pr.workspace_id, pr.partmaster_partnumber, pr.version,
                it.iteration if it else None,
            )
        pd_attrs = row.get("pathDataAttrs") or {}
        for s in selects:
            if s == "pr.partKey":
                continue
            val = _select_value(s, pr, master, it, row, db, attrs, pd_attrs)
            if val is not None:
                d[s] = val
        out_rows.append(d)
    return out_rows
