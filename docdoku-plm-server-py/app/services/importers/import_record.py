"""Import 记录 CRUD 服务。"""
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.schemas.import_ import ImportDTO


def create_import(db: Session, import_id: str, filename: str,
                  user_login: str, user_workspace_id: str) -> None:
    """插入一条 pending 导入记录（startdate=now, pending=true, succeed=false）。"""
    now = datetime.utcnow()
    db.execute(text(
        "INSERT INTO import (id, filename, startdate, pending, succeed, user_login, user_workspace_id) "
        "VALUES (:id, :fn, :now, true, false, :ul, :uw)"
    ), {"id": import_id, "fn": filename, "now": now, "ul": user_login, "uw": user_workspace_id})
    db.commit()


def complete_import(db: Session, import_id: str, succeed: bool,
                    errors: list[str], warnings: list[str]) -> None:
    """结束导入：pending=false, succeed=:s, enddate=now；写入 error/warning 子表。"""
    now = datetime.utcnow()
    db.execute(text(
        "UPDATE import SET pending=false, succeed=:s, enddate=:now WHERE id=:id"
    ), {"id": import_id, "s": succeed, "now": now})
    for e in errors:
        db.execute(text(
            "INSERT INTO import_error (import_id, errors) VALUES (:id, :e)"
        ), {"id": import_id, "e": e})
    for w in warnings:
        db.execute(text(
            "INSERT INTO import_warning (import_id, warnings) VALUES (:id, :w)"
        ), {"id": import_id, "w": w})
    db.commit()


def get_import(db: Session, import_id: str) -> ImportDTO | None:
    """按 id 读取，附带 errors/warnings 子表。不存在返回 None。"""
    row = db.execute(text(
        "SELECT id, filename, startdate, enddate, succeed, pending "
        "FROM import WHERE id=:id"
    ), {"id": import_id}).fetchone()
    if row is None:
        return None
    return _row_to_dto(db, row)


def list_imports(db: Session, user_workspace_id: str, filename: str) -> list[ImportDTO]:
    """列出某 workspace 下指定 filename 的所有导入记录（对齐 Java getImports(ws, filename)）。"""
    rows = db.execute(text(
        "SELECT id, filename, startdate, enddate, succeed, pending "
        "FROM import WHERE user_workspace_id=:uw AND filename=:fn "
        "ORDER BY startdate DESC"
    ), {"uw": user_workspace_id, "fn": filename}).fetchall()
    return [_row_to_dto(db, r) for r in rows]


def delete_import_record(db: Session, import_id: str) -> bool:
    """删除 import + 两个子表的行。存在则返回 True，否则 False。"""
    exists = db.execute(text(
        "SELECT 1 FROM import WHERE id=:id"
    ), {"id": import_id}).fetchone()
    if exists is None:
        return False
    db.execute(text("DELETE FROM import_error WHERE import_id=:id"), {"id": import_id})
    db.execute(text("DELETE FROM import_warning WHERE import_id=:id"), {"id": import_id})
    db.execute(text("DELETE FROM import WHERE id=:id"), {"id": import_id})
    db.commit()
    return True


def _row_to_dto(db: Session, row) -> ImportDTO:
    """把 import 行 + 子表 errors/warnings 组装为 ImportDTO。"""
    rid = row._mapping["id"]
    err_rows = db.execute(text(
        "SELECT errors FROM import_error WHERE import_id=:id"
    ), {"id": rid}).fetchall()
    warn_rows = db.execute(text(
        "SELECT warnings FROM import_warning WHERE import_id=:id"
    ), {"id": rid}).fetchall()
    return ImportDTO(
        id=row._mapping["id"],
        fileName=row._mapping["filename"],
        startDate=row._mapping["startdate"],
        endDate=row._mapping["enddate"],
        succeed=bool(row._mapping["succeed"]),
        pending=bool(row._mapping["pending"]),
        errors=[r._mapping["errors"] for r in err_rows],
        warnings=[r._mapping["warnings"] for r in warn_rows],
    )
