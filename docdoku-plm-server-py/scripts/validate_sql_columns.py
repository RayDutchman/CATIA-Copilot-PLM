#!/usr/bin/env python3
"""SQL 列名验证脚本 —— 扫描 app/ 中所有 raw text("SELECT...") / text("INSERT...")
调用，提取表名和列名，交叉验证 information_schema，报告不存在的列。

用法:
    python3 scripts/validate_sql_columns.py
"""

import ast
import re
import os
import sys
from collections import defaultdict
from pathlib import Path

import psycopg2

SCAN_DIR = Path(__file__).resolve().parent.parent / "app"
DB_URL = "host=localhost dbname=docdokuplm user=changeit password=changeit"

COLS_CACHE: dict[str, set[str]] = {}
TABLES_CACHE: set[str] = set()


def load_schema():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT table_name, column_name "
        "FROM information_schema.columns "
        "WHERE table_schema='public' "
        "ORDER BY table_name, ordinal_position"
    )
    for table, col in cur.fetchall():
        COLS_CACHE.setdefault(table, set()).add(col.lower())
    cur.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
    )
    for (table,) in cur.fetchall():
        TABLES_CACHE.add(table.lower())
    conn.close()


# ── SQL 提取 ──────────────────────────────────────

SELECT_RE = re.compile(r'\bSELECT\b', re.IGNORECASE)
INSERT_RE = re.compile(r'\bINSERT\s+INTO\b', re.IGNORECASE)

# 提取 "table.column" 或仅有 "column" 形式的列引用
QUALIFIED_COL_RE = re.compile(
    r'\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)\b', re.IGNORECASE
)
# FROM / JOIN 后的表名 (含别名)
FROM_RE = re.compile(
    r'\b(FROM|JOIN)\s+([a-z_][a-z0-9_]*)\b', re.IGNORECASE
)
# INSERT INTO 表名
INSERT_TABLE_RE = re.compile(
    r'INSERT\s+INTO\s+([a-z_][a-z0-9_]*)\b', re.IGNORECASE
)

# PostgreSQL 关键字——这些出现在 SQL 中很正常，不应报列名错误
PG_KEYWORDS = {
    "true", "false", "null", "as", "and", "or", "not", "in", "on", "is",
    "select", "from", "where", "join", "left", "right", "inner", "outer",
    "insert", "into", "values", "update", "set", "delete", "create", "alter",
    "table", "index", "view", "distinct", "limit", "offset", "order", "by",
    "group", "having", "union", "all", "any", "some", "exists", "case",
    "when", "then", "else", "end", "cast", "coalesce", "nullif",
    "asc", "desc", "returning", "on", "conflict", "do", "nothing",
    "now", "current_date", "current_timestamp", "count", "sum", "avg",
    "max", "min", "like", "ilike", "between", "cascade",
    "with", "recursive", "nextval", "serial", "primary", "key",
    "integer", "varchar", "text", "boolean", "timestamp", "float",
    "default", "unique", "references", "foreign",
}


def extract_sql_strings(source: str) -> list[tuple[int, str]]:
    """从源码中提取 text("...") 或 sql_text("...") 字符串，返回 (行号, SQL)。"""
    results = []
    for m in re.finditer(
        r'(?:text|sql_text)\s*\(\s*[\'"]((?:[^\'"]|\\.|[\'\"](?:[^\'\"]|\\.)*[\'\"])*?)[\'"]\s*\)',
        source, re.DOTALL,
    ):
        sql = m.group(1)
        # 简单清理多行字符串中的转义
        sql = sql.replace("\\n", "\n").replace("\\'", "'")
        # 确定行号
        lineno = source[: m.start()].count("\n") + 1
        results.append((lineno, sql))
    return results


def is_sql_statement(sql: str) -> bool:
    return bool(SELECT_RE.search(sql) or INSERT_RE.search(sql))


def parse_qualified_columns(sql: str) -> list[tuple[str, str]]:
    """提取 table.column 对。"""
    pairs = []
    for m in QUALIFIED_COL_RE.finditer(sql):
        alias = m.group(1).lower()
        col = m.group(2).lower()
        if col in PG_KEYWORDS:
            continue
        pairs.append((alias, col))
    return pairs


def parse_table_aliases(sql: str) -> dict[str, str]:
    """解析 FROM/JOIN table alias → 真实表名。"""
    mapping: dict[str, str] = {}
    for m in FROM_RE.finditer(sql):
        table = m.group(2).lower()
        if table in PG_KEYWORDS:
            continue
        mapping[table] = table
    # 查找 "table AS alias" 或 "table alias" 模式
    for m in re.finditer(
        r'\b(?:FROM|JOIN)\s+([a-z_][a-z0-9_]*)\s+(?:AS\s+)?([a-z_][a-z0-9_]*)\b',
        sql, re.IGNORECASE,
    ):
        table = m.group(1).lower()
        alias = m.group(2).lower()
        if table not in PG_KEYWORDS and alias not in ("on", "using", "where", "left", "right", "inner", "outer", "full", "cross", "natural"):
            mapping[alias] = table
    return mapping


def parse_insert_table(sql: str) -> str | None:
    m = INSERT_TABLE_RE.search(sql)
    return m.group(1).lower() if m else None


def find_mismatches(filepath: str, sql_rows: list[tuple[int, str]]) -> list[str]:
    issues = []
    for lineno, sql in sql_rows:
        if not is_sql_statement(sql):
            continue
        aliases = parse_table_aliases(sql)

        # 1) 检查 table.column 对
        for alias, col in parse_qualified_columns(sql):
            table = aliases.get(alias, alias)
            if table not in TABLES_CACHE:
                # 可能是临时表或 CTE，不在此检查
                continue
            columns = COLS_CACHE.get(table, set())
            if col not in columns:
                issues.append(
                    f"{filepath}:{lineno}  table.{col} → "
                    f"表 '{table}' 无列 '{col}'，实际列: {sorted(columns)[:8]}"
                )

        # 2) 检查 INSERT INTO table — 表存在性
        insert_table = parse_insert_table(sql)
        if insert_table and insert_table not in TABLES_CACHE:
            issues.append(
                f"{filepath}:{lineno}  INSERT INTO {insert_table} → 表不存在"
            )

    return issues


def scan_directory(root: Path) -> dict[str, list[str]]:
    all_issues: dict[str, list[str]] = defaultdict(list)
    for pyfile in root.rglob("*.py"):
        if "__pycache__" in str(pyfile):
            continue
        try:
            source = pyfile.read_text(encoding="utf-8")
        except Exception:
            continue
        sql_strings = extract_sql_strings(source)
        if not sql_strings:
            continue
        issues = find_mismatches(str(pyfile.relative_to(root.parent)), sql_strings)
        if issues:
            all_issues[str(pyfile)] = issues
    return dict(all_issues)


def main():
    print("加载 DB schema ...")
    load_schema()
    print(f"  {len(TABLES_CACHE)} 张表, {sum(len(v) for v in COLS_CACHE.values())} 列\n")

    issues = scan_directory(SCAN_DIR)
    if not issues:
        print("✅ 所有 SQL 列名与 DB schema 一致")
        return 0

    total = sum(len(v) for v in issues.values())
    print(f"❌ {len(issues)} 个文件, {total} 处列名/表名不匹配:\n")
    for filepath, msgs in sorted(issues.items()):
        print(f"── {filepath} ──")
        for msg in msgs:
            print(f"  {msg}")
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
