"""文档基线端点（DocumentBaselinesResource）。"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import BaselineNotFoundException, NotAllowedException
from app.models.auth import Account
from app.schemas.document import DocumentBaselineDTO
from app.services.documents.document_baseline_manager import document_baseline_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")

# 对齐 Java DocumentBaselineType enum: ordinal 0=LATEST, 1=RELEASED
_BASELINE_TYPE = {0: "LATEST", 1: "RELEASED"}


def _baseline_type_name(t):
    """int ordinal → Payara DocumentBaselineType 枚举名（对齐 JSON-B enum 序列化）"""
    if t is None:
        return None
    return _BASELINE_TYPE.get(t, "LATEST")


def _format_baseline(baseline: dict, db: Session, ws: str, *,
                     with_docs: bool = True) -> dict:
    """将 service 返回的 baseline dict 格式化为前端响应格式。"""
    author_login = baseline.get("authorLogin", "")
    author_name = author_login
    if author_login:
        acc = db.execute(sql_text(
            "SELECT name FROM account WHERE login = :l"
        ), {"l": author_login}).first()
        if acc and acc[0]:
            author_name = acc[0]
    return {
        "id": baseline["id"],
        "name": baseline.get("name", ""),
        "description": baseline.get("description", ""),
        "type": _baseline_type_name(baseline.get("type")),
        "creationDate": baseline["creationDate"].isoformat() + "Z"
        if baseline.get("creationDate") else None,
        "author": {
            "login": author_login,
            "name": author_name,
            "workspaceId": baseline.get("authorWorkspaceId", ws),
        },
        "baselinedDocuments": document_baseline_service.get_baselined_documents(
            db, baseline["id"]) if with_docs else [],
    }


@router.get("/workspaces/{ws}/document-baselines",
            response_model=List[DocumentBaselineDTO])
@router.get("/workspaces/{ws}/document-baselines/", include_in_schema=False)
def list_doc_baselines(ws: str,
                       current_user: Account = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    baselines = document_baseline_service.get_baselines(db, ws)
    return [_format_baseline(b, db, ws) for b in baselines]


@router.get("/workspaces/{ws}/document-baselines/{baseline_id}-light",
            response_model=DocumentBaselineDTO)
@router.get("/workspaces/{ws}/document-baselines/{baseline_id}-light/",
            include_in_schema=False)
def get_doc_baseline_light(ws: str, baseline_id: int,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """对齐 Java getBaselineLight：不含 baselinedDocuments 明细。"""
    b = document_baseline_service.get_baseline(db, ws, baseline_id)
    if not b:
        raise BaselineNotFoundException("BaselineNotFoundException", str(baseline_id))
    return _format_baseline(b, db, ws, with_docs=False)


@router.get("/workspaces/{ws}/document-baselines/{baseline_id}",
            response_model=DocumentBaselineDTO)
@router.get("/workspaces/{ws}/document-baselines/{baseline_id}/",
            include_in_schema=False)
def get_doc_baseline(ws: str, baseline_id: int,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """对齐 Java getBaseline：含 baselinedDocuments 明细。"""
    b = document_baseline_service.get_baseline(db, ws, baseline_id)
    if not b:
        raise BaselineNotFoundException("BaselineNotFoundException", str(baseline_id))
    return _format_baseline(b, db, ws, with_docs=True)


@router.post("/workspaces/{ws}/document-baselines", status_code=201)
@router.post("/workspaces/{ws}/document-baselines/", status_code=201,
             include_in_schema=False)
def create_doc_baseline(ws: str, body: dict,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    now = datetime.utcnow()
    baselined_docs = body.get("baselinedDocuments", [])

    raw_type = body.get("type", 0)
    if isinstance(raw_type, str):
        _TYPE_REVERSE = {"LATEST": 0, "RELEASED": 1}
        bl_type = _TYPE_REVERSE.get(raw_type.upper(), 0)
    else:
        bl_type = raw_type

    # ── 文档过滤逻辑（业务规则）──
    seen = set()
    accepted = []
    for doc in baselined_docs:
        dm_id = doc["documentMasterId"]
        version = doc.get("version", "A")
        key = (dm_id, version)
        if key in seen:
            continue
        seen.add(key)

        rev = db.execute(sql_text(
            "SELECT status, checkoutuser_login FROM documentrevision "
            "WHERE documentmaster_id=:dm AND workspace_id=:ws AND version=:ver"
        ), {"dm": dm_id, "ws": ws, "ver": version}).fetchone()
        if not rev:
            continue

        status, checkout_login = rev[0], rev[1]

        if bl_type == 1:  # RELEASED
            if status not in (1, 2):
                continue
            last_iter = db.execute(sql_text(
                "SELECT MAX(iteration) FROM documentiteration "
                "WHERE documentmaster_id=:dm AND workspace_id=:ws "
                "AND documentrevision_version=:ver"
            ), {"dm": dm_id, "ws": ws, "ver": version}).scalar()
            if not last_iter:
                continue
            iteration = last_iter
        else:  # LATEST (0)
            last_iter = db.execute(sql_text(
                "SELECT MAX(iteration) FROM documentiteration "
                "WHERE documentmaster_id=:dm AND workspace_id=:ws "
                "AND documentrevision_version=:ver"
            ), {"dm": dm_id, "ws": ws, "ver": version}).scalar()
            if not last_iter:
                continue
            if checkout_login:
                iteration = last_iter - 1
            else:
                iteration = last_iter
            if iteration < 1:
                continue

        accepted.append((dm_id, version, iteration))

    if not accepted:
        raise NotAllowedException("NotAllowedException66")

    # ── 委托 service 创建 ──
    result = document_baseline_service.create_baseline(
        db, ws, body.get("name", ""), body.get("description", ""),
        bl_type, accepted, current_user.login)

    return {
        "id": result["id"],
        "name": body.get("name", ""),
        "description": body.get("description", ""),
        "type": _baseline_type_name(bl_type),
        "creationDate": result["creationDate"].isoformat() + "Z",
        "author": {
            "login": current_user.login,
            "name": current_user.name or current_user.login,
            "workspaceId": ws,
        },
        "baselinedDocuments": [
            {"documentMasterId": dm_id, "version": version, "iteration": iteration}
            for dm_id, version, iteration in accepted
        ],
    }


@router.delete("/workspaces/{ws}/document-baselines/{baseline_id}",
               status_code=204)
@router.delete("/workspaces/{ws}/document-baselines/{baseline_id}/",
               status_code=204, include_in_schema=False)
def delete_doc_baseline(ws: str, baseline_id: int,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    document_baseline_service.delete_baseline(db, ws, baseline_id)
