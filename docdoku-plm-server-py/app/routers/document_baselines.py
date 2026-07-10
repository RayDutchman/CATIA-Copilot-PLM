"""文档基线端点（DocumentBaselinesResource）。"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import BaselineNotFoundException
from app.models.auth import Account
from app.schemas.document import DocumentBaselineDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")

# 对齐 Java DocumentBaselineType enum: ordinal 0=LATEST, 1=RELEASED
_BASELINE_TYPE = {0: "LATEST", 1: "RELEASED"}


def _baseline_type_name(t):
    """int ordinal → Payara DocumentBaselineType 枚举名（对齐 JSON-B enum 序列化）"""
    if t is None:
        return None
    return _BASELINE_TYPE.get(t, "LATEST")


def _baselined_documents(db: Session, baseline_id: int) -> list:
    docs = db.execute(sql_text(
        "SELECT bd.target_documentmaster_id, bd.target_docrevision_version, bd.target_iteration "
        "FROM baselineddocument bd WHERE bd.documentcollection_id = "
        "(SELECT documentcollection_id FROM documentbaseline WHERE id = :bid) "
        "ORDER BY bd.target_documentmaster_id"
    ), {"bid": baseline_id}).fetchall()
    return [
        {"documentMasterId": d[0], "version": d[1], "iteration": d[2]}
        for d in docs
    ]


def _baseline_to_dict(db: Session, r, ws: str, *, with_docs: bool = True) -> dict:
    """r 列顺序: id, name, description, type, creationdate, author_login, author_workspace_id"""
    author_login = r[5] or ""
    # 查 Account 表填充真实姓名
    author_name = author_login
    if author_login:
        acc = db.execute(sql_text(
            "SELECT name FROM account WHERE login = :l"
        ), {"l": author_login}).first()
        if acc and acc[0]:
            author_name = acc[0]
    return {
        "id": r[0],
        "name": r[1] or "",
        "description": r[2] or "",
        "type": _baseline_type_name(r[3]),
        "creationDate": r[4].isoformat() + "Z" if r[4] else None,
        "author": {
            "login": author_login,
            "name": author_name,
            "workspaceId": r[6] or ws,
        },
        "baselinedDocuments": _baselined_documents(db, r[0]) if with_docs else [],
    }


def _get_baseline_row(db: Session, ws: str, baseline_id: int):
    return db.execute(sql_text(
        "SELECT db.id, db.name, db.description, db.type, "
        "db.creationdate, db.author_login, db.author_workspace_id "
        "FROM documentbaseline db WHERE db.id = :bid"
    ), {"bid": baseline_id}).fetchone()


@router.get("/workspaces/{ws}/document-baselines", response_model=List[DocumentBaselineDTO])
@router.get("/workspaces/{ws}/document-baselines/", include_in_schema=False)
def list_doc_baselines(ws: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    rows = db.execute(sql_text(
        "SELECT DISTINCT db.id, db.name, db.description, db.type, "
        "db.creationdate, db.author_login, db.author_workspace_id "
        "FROM documentbaseline db "
        "JOIN baselineddocument bd ON db.documentcollection_id = bd.documentcollection_id "
        "WHERE bd.target_workspace_id = :ws "
        "ORDER BY db.id"
    ), {"ws": ws}).fetchall()
    return [_baseline_to_dict(db, r, ws) for r in rows]


@router.get("/workspaces/{ws}/document-baselines/{baseline_id}-light",
            response_model=DocumentBaselineDTO)
@router.get("/workspaces/{ws}/document-baselines/{baseline_id}-light/", include_in_schema=False)
def get_doc_baseline_light(ws: str, baseline_id: int,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """对齐 Java getBaselineLight：不含 baselinedDocuments 明细。"""
    r = _get_baseline_row(db, ws, baseline_id)
    if not r:
        raise BaselineNotFoundException("BaselineNotFoundException", str(baseline_id))
    return _baseline_to_dict(db, r, ws, with_docs=False)


@router.get("/workspaces/{ws}/document-baselines/{baseline_id}",
            response_model=DocumentBaselineDTO)
@router.get("/workspaces/{ws}/document-baselines/{baseline_id}/", include_in_schema=False)
def get_doc_baseline(ws: str, baseline_id: int,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """对齐 Java getBaseline：含 baselinedDocuments 明细。"""
    r = _get_baseline_row(db, ws, baseline_id)
    if not r:
        raise BaselineNotFoundException("BaselineNotFoundException", str(baseline_id))
    return _baseline_to_dict(db, r, ws, with_docs=True)


@router.post("/workspaces/{ws}/document-baselines", status_code=201)
@router.post("/workspaces/{ws}/document-baselines/", status_code=201, include_in_schema=False)
def create_doc_baseline(ws: str, body: dict,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    now = datetime.utcnow()
    baselined_docs = body.get("baselinedDocuments", [])
    if not baselined_docs:
        raise HTTPException(400, "No baselinedDocuments provided")
    result = db.execute(sql_text(
        "INSERT INTO documentcollection (creationdate, author_workspace_id, author_login) "
        "VALUES (:now, :ws, :login) RETURNING id"
    ), {"now": now, "ws": ws, "login": current_user.login})
    collection_id = result.fetchone()[0]
    result = db.execute(sql_text(
        "INSERT INTO documentbaseline (creationdate, description, name, type, "
        "author_workspace_id, author_login, documentcollection_id) "
        "VALUES (:now, :desc, :name, :type, :ws, :login, :col_id) RETURNING id"
    ), {
        "now": now, "desc": body.get("description", ""),
        "name": body.get("name", ""), "type": body.get("type", 0),
        "ws": ws, "login": current_user.login, "col_id": collection_id
    })
    baseline_id = result.fetchone()[0]
    for doc in baselined_docs:
        db.execute(sql_text(
            "INSERT INTO baselineddocument (target_iteration, documentcollection_id, "
            "target_documentmaster_id, target_docrevision_version, target_workspace_id) "
            "VALUES (:iter, :col_id, :dm_id, :ver, :ws)"
        ), {
            "iter": doc.get("iteration", 1),
            "col_id": collection_id,
            "dm_id": doc["documentMasterId"],
            "ver": doc.get("version", "A"),
            "ws": ws
        })
    db.commit()
    docs = db.execute(sql_text(
        "SELECT bd.target_documentmaster_id, bd.target_docrevision_version, bd.target_iteration "
        "FROM baselineddocument bd WHERE bd.documentcollection_id = :cid "
        "ORDER BY bd.target_documentmaster_id"
    ), {"cid": collection_id}).fetchall()
    return {
        "id": baseline_id, "name": body.get("name", ""),
        "description": body.get("description", ""),
        "type": _baseline_type_name(body.get("type", 0)),
        "creationDate": now.isoformat() + "Z",
        "author": {"login": current_user.login, "name": current_user.name or current_user.login, "workspaceId": ws},
        "baselinedDocuments": [
            {"documentMasterId": d[0], "version": d[1], "iteration": d[2]}
            for d in docs
        ],
    }


@router.delete("/workspaces/{ws}/document-baselines/{baseline_id}", status_code=204)
@router.delete("/workspaces/{ws}/document-baselines/{baseline_id}/", status_code=204, include_in_schema=False)
def delete_doc_baseline(ws: str, baseline_id: int,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    baseline = db.execute(sql_text(
        "SELECT documentcollection_id FROM documentbaseline WHERE id = :bid"
    ), {"bid": baseline_id}).fetchone()
    if not baseline:
        raise BaselineNotFoundException("BaselineNotFoundException", str(baseline_id))
    collection_id = baseline[0]
    db.execute(sql_text("DELETE FROM baselineddocument WHERE documentcollection_id = :cid"), {"cid": collection_id})
    db.execute(sql_text("DELETE FROM documentbaseline WHERE id = :bid"), {"bid": baseline_id})
    db.execute(sql_text("DELETE FROM documentcollection WHERE id = :cid"), {"cid": collection_id})
    db.commit()
