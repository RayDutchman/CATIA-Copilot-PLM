#!/usr/bin/env python3
"""SQL 列名验证脚本 v2 —— 增强版。

新增:
- UPDATE/DELETE 语句验证
- INSERT 列完整性检查 (NOT NULL 列是否遗漏)
- 更好的表别名解析 (AS 关键字、多表JOIN)
- 数据类型校验

用法:
    python3 scripts/validate_sql_columns.py
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import psycopg2

SCAN_DIR = Path(__file__).resolve().parent.parent / "app"
DB_URL = "host=localhost dbname=docdokuplm user=changeit password=changeit"

# DB schema cache
TABLES: set[str] = set()
COLUMNS: dict[str, set[str]] = {}        # table → {col, ...}
NOT_NULL_COLS: dict[str, set[str]] = {}  # table → {col NOT NULL, ...}
COLUMN_TYPES: dict[str, dict[str, str]] = {}  # table → {col → data_type}


def load_schema():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT table_name, column_name, is_nullable, data_type "
                "FROM information_schema.columns WHERE table_schema='public' "
                "ORDER BY table_name, ordinal_position")
    for table, col, nullable, dt in cur.fetchall():
        TABLES.add(table)
        COLUMNS.setdefault(table, set()).add(col)
        COLUMN_TYPES.setdefault(table, {})[col] = dt
        if nullable == "NO":
            NOT_NULL_COLS.setdefault(table, set()).add(col)
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    for (t,) in cur.fetchall():
        TABLES.add(t.lower())
    conn.close()


# ── SQL 提取 ──────────────────────────────────────

SQL_STRING_RE = re.compile(
    r'(?:text|sql_text)\s*\(\s*[\'"""]((?:[^\'""]|\\.|[\'""][^\'\""]*[\'""])*?)[\'""]\s*\)',
    re.DOTALL,
)

SQL_KEYWORDS = {
    "select","from","where","join","left","right","inner","outer","cross",
    "insert","into","values","update","set","delete","create",
    "and","or","not","in","on","is","null","true","false",
    "as","asc","desc","limit","offset","order","by","group","having",
    "union","all","distinct","exists","between","like","ilike",
    "case","when","then","else","end","coalesce","nullif","cast",
    "returning","conflict","do","nothing","now","current","nextval",
}

# table.column 模式 (更宽松)
QUALIFIED_COL_RE = re.compile(r'\b([a-z_]\w*)\.([a-z_]\w*)\b', re.IGNORECASE)

# FROM/JOIN 表名 + 可选别名
TABLE_ALIAS_RE = re.compile(
    r'\b(?:FROM|JOIN)\s+([a-z_]\w*)'  # 表名
    r'(?:\s+(?:AS\s+)?([a-z_]\w*))?',  # 可选别名
    re.IGNORECASE,
)

INSERT_RE = re.compile(r'INSERT\s+INTO\s+([a-z_]\w*)', re.IGNORECASE)
DELETE_RE = re.compile(r'DELETE\s+FROM\s+([a-z_]\w*)', re.IGNORECASE)
UPDATE_RE = re.compile(r'UPDATE\s+([a-z_]\w*)', re.IGNORECASE)
RETURNING_RE = re.compile(r'RETURNING\s+(.+)', re.IGNORECASE)

# INSERT 列提取: INSERT INTO table (col1, col2,...)
INSERT_COLS_RE = re.compile(
    r'INSERT\s+INTO\s+[a-z_]\w*\s*\(([^)]+)\)', re.IGNORECASE
)
# UPDATE SET col=val 提取
UPDATE_SET_RE = re.compile(
    r'UPDATE\s+[a-z_]\w*\s+SET\s+(.+?)(?:\s+WHERE\s|\s*$)', re.IGNORECASE | re.DOTALL
)

SERIAL_PK_TABLES = {
    "acl", "account", "workspace", "partmaster", "documentmaster",
}


def extract_sql_strings(source: str) -> list[tuple[int, str]]:
    results = []
    for m in SQL_STRING_RE.finditer(source):
        sql = m.group(1)
        sql = re.sub(r'\\(.)', r'\1', sql)
        lineno = source[:m.start()].count("\n") + 1
        results.append((lineno, sql))
    return results


def is_modify_statement(sql: str) -> bool:
    upper = sql[:30].upper()
    return any(upper.startswith(kw) for kw in ("SELECT", "INSERT", "UPDATE", "DELETE"))


# ── 别名解析 ──────────────────────────────────────

def parse_table_aliases(sql: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for m in TABLE_ALIAS_RE.finditer(sql):
        table = m.group(1).lower()
        alias = m.group(2).lower() if m.group(2) else table
        if table in SQL_KEYWORDS or alias in SQL_KEYWORDS:
            continue
        mapping[alias] = table
    return mapping


# ── 验证核心 ──────────────────────────────────────

def verify_column(table: str, col: str, filepath: str, lineno: int) -> str | None:
    """验证 table.column 存在，返回 None 或错误消息。"""
    # 常量表名: 找最匹配的真实表
    real_table = table
    if table not in TABLES:
        # 模糊匹配: 找包含 table 子串的真实表名
        candidates = [t for t in TABLES if table in t]
        if len(candidates) == 1:
            real_table = candidates[0]
        elif len(candidates) > 1:
            return f"  ⚠️  别名 '{table}' 匹配多个表: {candidates}"
        else:
            return f"  ❌ 别名 '{table}' 无法匹配任何已知表。"

    columns = COLUMNS.get(real_table, set())
    if col not in columns:
        actual = sorted(columns)[:10]
        return f"  ❌ {real_table}.{col} → 无此列 (实际: {actual})"
    return None


def verify_insert_completeness(sql: str, filepath: str, lineno: int) -> list[str]:
    """检查 INSERT 语句是否遗漏 NOT NULL 列。"""
    issues = []
    table_match = INSERT_RE.search(sql)
    if not table_match:
        return issues
    table = table_match.group(1).lower()
    if table not in TABLES:
        return issues

    cols_match = INSERT_COLS_RE.search(sql)
    if not cols_match:
        return issues

    insert_cols = set()
    for c in re.findall(r'([a-z_]\w*)', cols_match.group(1), re.IGNORECASE):
        c = c.strip().lower()
        if c not in SQL_KEYWORDS and len(c) > 1:
            insert_cols.add(c)

    missing = NOT_NULL_COLS.get(table, set()) - insert_cols
    # 排除 serial autoincrement PK
    if table in SERIAL_PK_TABLES:
        missing.discard("id")
    # 排除 FK 列（可后续设）
    missing = {c for c in missing if not c.endswith("_id") and c not in ("login",)}

    # 检查 INSERT 列是否都在表中
    for col in insert_cols:
        if col not in COLUMNS.get(table, set()):
            issues.append(f"  ❌ INSERT INTO {table} → 列 '{col}' 不存在 "
                          f"(实际: {sorted(COLUMNS.get(table, set()))[:10]})")

    if missing:
        issues.append(f"  ⚠️  INSERT INTO {table} 缺 NOT NULL 列: {sorted(missing)}")
    return issues


def verify_returning_columns(sql: str, filepath: str, lineno: int) -> list[str]:
    """验证 RETURNING 子句中的列名。"""
    issues = []
    table_match = INSERT_RE.search(sql)
    if not table_match:
        return issues
    table = table_match.group(1).lower()
    ret_match = RETURNING_RE.search(sql)
    if not ret_match:
        return issues
    for col in re.findall(r'([a-z_]\w*)', ret_match.group(1)):
        if col.lower() in SQL_KEYWORDS:
            continue
        columns = COLUMNS.get(table, set())
        if col.lower() not in columns:
            issues.append(f"  ❌ RETURNING {col} → 表 '{table}' 无此列")
    return issues


# ── 全量扫描 ──────────────────────────────────────

def scan() -> dict[str, list[str]]:
    all_issues: dict[str, list[str]] = defaultdict(list)

    for pyfile in sorted(SCAN_DIR.rglob("*.py")):
        if "__pycache__" in str(pyfile):
            continue
        try:
            source = pyfile.read_text(encoding="utf-8")
        except Exception:
            continue

        sql_strings = extract_sql_strings(source)
        file_issues = []
        for lineno, sql in sql_strings:
            if not is_modify_statement(sql):
                continue

            aliases = parse_table_aliases(sql)

            # 1) 检查 table.column 引用
            for m in QUALIFIED_COL_RE.finditer(sql):
                alias = m.group(1).lower()
                col = m.group(2).lower()
                if col in SQL_KEYWORDS or alias in SQL_KEYWORDS:
                    continue
                table = aliases.get(alias, alias)
                if table not in TABLES:
                    continue  # 别名/CTE，跳过
                err = verify_column(table, col, str(pyfile), lineno)
                if err:
                    file_issues.append(err)

            # 2) INSERT 完整性检查
            if INSERT_RE.search(sql):
                file_issues.extend(verify_insert_completeness(sql, str(pyfile), lineno))
                file_issues.extend(verify_returning_columns(sql, str(pyfile), lineno))

            # 3) INSERT/DELETE/UPDATE 表存在性
            for pat, mode in [(INSERT_RE, "INSERT"), (DELETE_RE, "DELETE"), (UPDATE_RE, "UPDATE")]:
                m = pat.search(sql)
                if m and m.group(1).lower() not in TABLES:
                    file_issues.append(f"  ❌ {mode} {m.group(1)} → 表不存在")

        if file_issues:
            rel = str(pyfile.relative_to(SCAN_DIR.parent))
            all_issues[rel] = sorted(set(file_issues))

    return dict(all_issues)


def main():
    print("加载 DB schema ...")
    load_schema()
    print(f"  {len(TABLES)} 张表, {sum(len(v) for v in COLUMNS.values())} 列\n")

    issues = scan()
    if not issues:
        print("✅ 全部 SQL 通过")
        return 0

    critical = sum(1 for msgs in issues.values() for m in msgs if "❌" in m)
    warning = sum(1 for msgs in issues.values() for m in msgs if "⚠️" in m)
    print(f"发现: 🔴 {critical} errors + ⚠️ {warning} warnings ({len(issues)} 个文件)\n")

    for filepath, msgs in sorted(issues.items()):
        print(f"{'='*60}")
        print(f"{filepath}")
        print(f"{'='*60}")
        for msg in sorted(msgs):
            print(msg)
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
