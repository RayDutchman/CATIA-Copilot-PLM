"""自定义查询执行引擎（对齐 Payara PartRevisionQueryDAO / QueryPredicateBuilder）。

将前端 QueryRule 树编译为参数化 SQL 的 WHERE 片段，执行后按权限/检入状态后过滤，
返回 PartRevision ORM 列表供 part_mapper.map_revision 映射为 DTO。
"""
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.product.part_revision import PartRevision
from app.services.factory.acl_factory import check_read_access

# 版本状态字符串 → 整数（对齐 partrevision.status: 0=WIP/1=RELEASED/2=OBSOLETE）
_STATUS_MAP = {"WIP": 0, "RELEASED": 1, "OBSOLETE": 2}

# 属性字段前缀 → (dtype 判别值, instanceattribute 值列名, 值类型)
# dtype 判别值对齐 product_structure._DTYPE_TO_TYPE 的键（EclipseLink 单表继承类名）
_ATTR_PREFIXES = {
    "attr-TEXT.": ("InstanceTextAttribute", "textvalue", "string"),
    "attr-LONG_TEXT.": ("InstanceLongTextAttribute", "longtextvalue", "string"),
    "attr-DATE.": ("InstanceDateAttribute", "datevalue", "date"),
    "attr-BOOLEAN.": ("InstanceBooleanAttribute", "booleanvalue", "boolean"),
    "attr-URL.": ("InstanceURLAttribute", "urlvalue", "string"),
    "attr-NUMBER.": ("InstanceNumberAttribute", "numbervalue", "double"),
    "attr-LOV.": ("InstanceListOfValuesAttribute", "indexvalue", "lov"),
    "attr-PART_NUMBER.": ("InstancePartNumberAttribute", "partmaster_partnumber", "string"),
}

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")


def _parse_date(value):
    """解析日期字符串（对齐 Java DateUtils，宽松兼容多格式）。"""
    if isinstance(value, datetime):
        return value
    s = str(value).strip().replace("Z", "")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # 兜底：ISO 解析
    return datetime.fromisoformat(s[:19])


def _coerce(value, vtype):
    """按值类型强制转换（对齐 QueryPredicateBuilder 的类型系统）。"""
    if vtype == "double":
        return float(value)
    if vtype == "date":
        return _parse_date(value)
    if vtype == "boolean":
        return str(value).strip().lower() in ("true", "1", "yes")
    if vtype == "lov":
        return int(value)
    if vtype == "status":
        s = str(value).strip()
        return _STATUS_MAP.get(s.upper(), None) if s.upper() in _STATUS_MAP else int(s)
    return str(value)


def _cmp(col, operator, vtype, values, params):
    """生成单个字段的比较 SQL 片段，向 params 填入参数（对齐 QueryPredicateBuilder）。"""
    def add(v):
        key = f"p{len(params)}"
        params[key] = v
        return key

    v0 = values[0] if values else None

    # LIKE 语义（contains/begins_with/ends_with，仅字符串）
    like_map = {
        "contains": "%{}%", "not_contains": "%{}%",
        "begins_with": "{}%", "not_begins_with": "{}%",
        "ends_with": "%{}", "not_ends_with": "%{}",
    }
    if operator in like_map:
        key = add(like_map[operator].format(str(v0)))
        frag = f"{col} LIKE :{key}"
        return f"NOT ({frag})" if operator.startswith("not_") else frag

    if operator == "equal":
        if vtype == "date":
            d = _coerce(v0, "date")
            k1, k2 = add(d), add(d + timedelta(days=1))
            return f"({col} >= :{k1} AND {col} < :{k2})"
        return f"{col} = :{add(_coerce(v0, vtype))}"

    if operator == "not_equal":
        if vtype == "date":
            d = _coerce(v0, "date")
            k1, k2 = add(d), add(d + timedelta(days=1))
            return f"NOT ({col} >= :{k1} AND {col} < :{k2})"
        return f"{col} <> :{add(_coerce(v0, vtype))}"

    op_sql = {"less": "<", "less_or_equal": "<=", "greater": ">", "greater_or_equal": ">="}
    if operator in op_sql:
        return f"{col} {op_sql[operator]} :{add(_coerce(v0, vtype))}"

    if operator == "between" and len(values) >= 2:
        k1, k2 = add(_coerce(values[0], vtype)), add(_coerce(values[1], vtype))
        return f"{col} BETWEEN :{k1} AND :{k2}"

    # 未知运算符 → 恒真（不破坏整体查询）
    return "1=1"


def _attr_exists(prefix, field, operator, values, params):
    """属性叶子 → EXISTS 子查询（按需 join，避免笛卡尔积；优于 Java 无条件 cross join）。"""
    dtype, valcol, vtype = _ATTR_PREFIXES[prefix]
    attr_name = field[len(prefix):]
    dtype_key = f"p{len(params)}"
    params[dtype_key] = dtype
    name_key = f"p{len(params)}"
    params[name_key] = attr_name
    inner = _cmp(f"ia.{valcol}", operator, vtype, values, params)
    return (
        "EXISTS (SELECT 1 FROM partiteration_attribute pa "
        "JOIN instanceattribute ia ON ia.id = pa.instanceattribute_id "
        "WHERE pa.workspace_id = pr.workspace_id "
        "AND pa.partmaster_partnumber = pr.partmaster_partnumber "
        "AND pa.partrevision_version = pr.version "
        f"AND ia.dtype = :{dtype_key} AND ia.name = :{name_key} AND {inner})"
    )


def _pr_leaf(sub, operator, rtype, values, params):
    """pr.* 前缀特殊路由（对齐 PartRevisionQueryDAO.getPartRevisionPredicate）。"""
    if sub == "linkedDocuments":
        return "1=1"  # Java 预留未实现，恒真
    if sub == "lifeCycleState":
        return "1=1"  # 无对应列（由 workflow 派生），恒真以免生成非法 SQL
    if sub == "status":
        return _cmp("pr.status", operator, "status", values, params)
    if sub in ("checkInDate", "modificationDate"):
        col = "pit.checkindate" if sub == "checkInDate" else "pit.modificationdate"
        inner = _cmp(col, operator, "date", values, params)
        # 末迭代约束：仅对最新 iteration 生效
        return (
            "EXISTS (SELECT 1 FROM partiteration pit WHERE pit.workspace_id = pr.workspace_id "
            "AND pit.partmaster_partnumber = pr.partmaster_partnumber "
            "AND pit.partrevision_version = pr.version "
            "AND pit.iteration = (SELECT max(pit2.iteration) FROM partiteration pit2 "
            "WHERE pit2.workspace_id = pr.workspace_id "
            "AND pit2.partmaster_partnumber = pr.partmaster_partnumber "
            "AND pit2.partrevision_version = pr.version) "
            f"AND {inner})"
        )
    if sub == "tags":
        clauses = []
        for v in values:
            key = f"p{len(params)}"
            params[key] = v
            clauses.append(
                "EXISTS (SELECT 1 FROM partrevision_tag t "
                "WHERE t.partmaster_workspace_id = pr.workspace_id "
                "AND t.partmaster_partnumber = pr.partmaster_partnumber "
                "AND t.partrevision_version = pr.version "
                f"AND t.tag_label = :{key})"
            )
        return "(" + " OR ".join(clauses) + ")" if clauses else "1=1"
    if sub == "creationDate":
        return _cmp("pr.creationdate", operator, "date", values, params)
    if sub == "version":
        return _cmp("pr.version", operator, "string", values, params)
    # 其他 pr 列名按 rule.type 直译
    vtype = {"double": "double", "date": "date", "status": "status"}.get(rtype, "string")
    return _cmp(f"pr.{sub.lower()}", operator, vtype, values, params)


def _leaf_predicate(rule, params):
    """叶子规则 → SQL 片段（按 field 前缀路由，对齐 PartRevisionQueryDAO.getRulePredicate）。"""
    field = rule.get("field") or ""
    operator = rule.get("operator")
    rtype = rule.get("type") or "string"
    values = rule.get("values") or []

    if field.startswith("pm."):
        sub = field[3:]
        col_map = {
            "number": "pm.partnumber", "name": "pm.name",
            "type": "pm.type", "standardPart": "pm.standardpart",
        }
        col = col_map.get(sub, f"pm.{sub.lower()}")
        vtype = "boolean" if sub == "standardPart" else "string"
        return _cmp(col, operator, vtype, values, params)

    if field.startswith("pr."):
        return _pr_leaf(field[3:], operator, rtype, values, params)

    if field.startswith("author."):
        sub = field[7:]
        if sub == "login":
            return _cmp("pr.author_login", operator, "string", values, params)
        # author.name → account 表 EXISTS
        inner = _cmp("acc.name", operator, "string", values, params)
        return f"EXISTS (SELECT 1 FROM account acc WHERE acc.login = pr.author_login AND {inner})"

    for prefix in _ATTR_PREFIXES:
        if field.startswith(prefix):
            return _attr_exists(prefix, field, operator, values, params)

    # 未知字段 → 恒真
    return "1=1"


def build_part_where(rule, params, joins=None):
    """递归编译 QueryRule 树为 WHERE 片段（非叶子按 condition 组合 AND/OR）。"""
    if rule is None:
        return "1=1"
    sub_rules = rule.get("rules") or []
    if sub_rules:
        cond = (rule.get("condition") or "AND").upper()
        joiner = " OR " if cond == "OR" else " AND "
        parts = [build_part_where(r, params) for r in sub_rules]
        parts = [p for p in parts if p and p != "1=1"] or ["1=1"]
        return "(" + joiner.join(parts) + ")"
    return _leaf_predicate(rule, params)


def run_part_query(db: Session, workspace_id: str, query: dict,
                   user_login: str, is_admin: bool) -> list:
    """执行 PartRevision 查询：编译 WHERE → 查主键 → 加载 ORM → 权限/检入后过滤。

    对齐 Payara PartRevisionQueryDAO.runQuery + ProductManagerBean.searchPartRevisions：
    - 仅保留有已检入迭代的版本（getLastCheckedInIteration != null）
    - 剔除无读取权限的版本（hasPartRevisionReadAccess）
    """
    rule = query.get("queryRule")
    params = {"__ws": workspace_id}
    where = build_part_where(rule, params)
    sql = (
        "SELECT DISTINCT pr.workspace_id, pr.partmaster_partnumber, pr.version "
        "FROM partrevision pr "
        "JOIN partmaster pm ON pm.workspace_id = pr.workspace_id "
        "AND pm.partnumber = pr.partmaster_partnumber "
        "WHERE pr.workspace_id = :__ws AND (" + where + ")"
    )
    rows = db.execute(text(sql), params).fetchall()
    result = []
    for r in rows:
        pr = db.get(PartRevision, {
            "workspace_id": r[0], "partmaster_partnumber": r[1], "version": r[2],
        })
        if pr is None:
            continue
        # 后过滤：必须有已检入迭代
        if not any(it.check_in_date is not None for it in (pr.iterations or [])):
            continue
        # 后过滤：读取权限
        if not check_read_access(db, pr.acl_id, user_login, is_admin, workspace_id):
            continue
        result.append(pr)
    return result
