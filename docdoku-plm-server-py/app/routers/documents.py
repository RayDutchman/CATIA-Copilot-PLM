"""文档集合路由（DocumentsResource）。"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, text as sql_text
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.document import DocumentRevision, DocumentMaster
from app.services.document_manager import DocumentService
from app.routers.document import _doc_to_dict
from app.schemas.document import DocumentRevisionDTO

router = APIRouter()
svc = DocumentService()


@router.get("/workspaces/{ws}/documents/count")
@router.get("/workspaces/{ws}/documents/count/", include_in_schema=False)
def count(ws: str, current_user: Account = Depends(get_current_user),
          db: Session = Depends(get_db)):
    return {"count": svc.count_documents(db, ws)}


@router.get("/workspaces/{ws}/documents/search", response_model=List[DocumentRevisionDTO])
@router.get("/workspaces/{ws}/documents/search/", include_in_schema=False)
def search_documents(
    ws: str,
    id: str = Query("", alias="id"),
    title: str = Query(""),
    version: str = Query(""),
    author: str = Query(""),
    tags: str = Query(""),
    content: str = Query(""),
    createdFrom: str = Query(""),
    createdTo: str = Query(""),
    modifiedFrom: str = Query(""),
    modifiedTo: str = Query(""),
    attributes: str = Query(""),
    q: str = Query(""),
    start: int = Query(0, alias="from"),
    size: int = Query(20),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    from app.services.indexer.indexer_query_builder import es_query_builder

    # ES 优先搜索
    try:
        es_params = {"from": start, "size": size}
        if q: es_params["q"] = q
        if id: es_params["id"] = id
        if title: es_params["title"] = title
        if version: es_params["version"] = version
        if author: es_params["author"] = author
        if createdFrom: es_params["createdFrom"] = createdFrom
        if createdTo: es_params["createdTo"] = createdTo
        if modifiedFrom: es_params["modifiedFrom"] = modifiedFrom
        if modifiedTo: es_params["modifiedTo"] = modifiedTo
        if tags: es_params["tags"] = tags
        if content: es_params["content"] = content
        keys = es_query_builder.search_documents(ws, es_params)
        if keys:
            # 解析迭代级 key: '{docMId}-{version}-{iteration}' → 按 revision 去重
            from sqlalchemy.orm import joinedload
            seen = set()
            rev_keys = []
            for k in keys:
                parts = k.rsplit("-", 2)
                if len(parts) >= 2:
                    dv = (parts[0], parts[1])  # (docMId, version)
                    if dv not in seen:
                        seen.add(dv)
                        rev_keys.append(dv)
            if rev_keys:
                from sqlalchemy import and_
                conditions = [
                    (DocumentRevision.workspace_id == ws) &
                    (DocumentRevision.documentmaster_id == dv[0]) &
                    (DocumentRevision.version == dv[1])
                    for dv in rev_keys
                ]
                revisions = db.query(DocumentRevision).options(
                    joinedload(DocumentRevision.iterations),
                ).filter(or_(*conditions)).all()
                rev_map = {(dr.documentmaster_id, dr.version): dr for dr in revisions}
                ordered = [rev_map[k] for k in rev_keys if k in rev_map]
                return [_doc_to_dict(db, dr, current_user.login) for dr in ordered]
    except Exception:
        pass  # ES 失败 → fallback

    # DB LIKE fallback ────────────────────────────────────────
    query = db.query(DocumentRevision).join(
        DocumentMaster,
        (DocumentRevision.workspace_id == DocumentMaster.workspace_id) &
        (DocumentRevision.documentmaster_id == DocumentMaster.id)
    ).filter(DocumentMaster.workspace_id == ws)
    if q:
        q_pattern = f"%{q}%"
        query = query.filter(or_(
            DocumentMaster.id.ilike(q_pattern),
            DocumentRevision.title.ilike(q_pattern),
        ))
    if id:
        query = query.filter(DocumentMaster.id.ilike(f"%{id}%"))
    if title:
        query = query.filter(DocumentRevision.title.ilike(f"%{title}%"))
    if version:
        query = query.filter(DocumentRevision.version == version)
    if author:
        query = query.filter(DocumentRevision.author_login == author)
    if tags:
        matched_ids = [row[0] for row in db.execute(sql_text(
            "SELECT dr.documentmaster_id FROM documentrevision dr "
            "JOIN documentrevision_tag t ON dr.documentmaster_id=t.documentmaster_id "
            "AND dr.version=t.documentrevision_version "
            "WHERE t.tag_label ILIKE :t AND dr.workspace_id=:w"
        ), {"t": f"%{tags}%", "w": ws}).fetchall()]
        query = query.filter(DocumentRevision.documentmaster_id.in_(matched_ids))
    if content:
        content_pattern = f"%{content}%"
        from app.models.document import DocumentIteration
        matched_ids = [row[0] for row in db.execute(sql_text(
            "SELECT DISTINCT di.documentmaster_id FROM documentiteration di "
            "WHERE di.workspace_id = :w AND di.revisionnote ILIKE :c"
        ), {"w": ws, "c": f"%{content}%"}).fetchall()]
        if matched_ids:
            query = query.filter(DocumentRevision.documentmaster_id.in_(matched_ids))
        else:
            query = query.filter(DocumentRevision.documentmaster_id == None)
    if createdFrom:
        cf = datetime.fromisoformat(createdFrom)
        query = query.filter(DocumentRevision.creation_date >= cf)
    if createdTo:
        ct = datetime.fromisoformat(createdTo)
        query = query.filter(DocumentRevision.creation_date <= ct)
    if modifiedFrom:
        from app.models.document import DocumentIteration as DI
        mf = datetime.fromisoformat(modifiedFrom)
        matched_ids = [row[0] for row in db.execute(sql_text(
            "SELECT DISTINCT di.documentmaster_id FROM documentiteration di "
            "WHERE di.workspace_id = :w AND di.modificationdate >= :d"
        ), {"w": ws, "d": mf}).fetchall()]
        if matched_ids:
            query = query.filter(DocumentRevision.documentmaster_id.in_(matched_ids))
        else:
            query = query.filter(DocumentRevision.documentmaster_id == None)
    if modifiedTo:
        from app.models.document import DocumentIteration as DI
        mt = datetime.fromisoformat(modifiedTo)
        matched_ids = [row[0] for row in db.execute(sql_text(
            "SELECT DISTINCT di.documentmaster_id FROM documentiteration di "
            "WHERE di.workspace_id = :w AND di.modificationdate <= :d"
        ), {"w": ws, "d": mt}).fetchall()]
        if matched_ids:
            query = query.filter(DocumentRevision.documentmaster_id.in_(matched_ids))
        else:
            query = query.filter(DocumentRevision.documentmaster_id == None)
    docs = query.order_by(DocumentMaster.id).offset(start).limit(size).all()
    return [_doc_to_dict(db, d, current_user.login) for d in docs]


@router.get("/workspaces/{ws}/documents", response_model=List[DocumentRevisionDTO])
@router.get("/workspaces/{ws}/documents/", include_in_schema=False)
def list_docs(ws: str, start: int = Query(0, ge=0),
              max: int = Query(50, ge=1, le=500),
              length: int = Query(None, ge=1, le=500),
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    limit = length or max
    return [_doc_to_dict(db, r, current_user.login) for r in svc.list_revisions(db, ws, start, limit)]


@router.get("/workspaces/{ws}/documents/checkedout", response_model=List[DocumentRevisionDTO])
@router.get("/workspaces/{ws}/documents/checkedout/", include_in_schema=False)
def list_checked_out(ws: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    return [_doc_to_dict(db, r, current_user.login) for r in svc.list_checked_out(db, ws)]


@router.get("/workspaces/{ws}/documents/countCheckedOut")
@router.get("/workspaces/{ws}/documents/countCheckedOut/", include_in_schema=False)
def count_checked_out(ws: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    return {"count": svc.count_checked_out_documents(db, ws)}


@router.get("/workspaces/{ws}/documents/doc_revs", response_model=List[DocumentRevisionDTO])
@router.get("/workspaces/{ws}/documents/doc_revs/", include_in_schema=False)
def search_doc_revs(ws: str, q: str = Query(""),
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return [{"workspaceId": r.workspace_id, "docMasterId": r.documentmaster_id,
             "title": r.title, "version": r.version}
            for r in svc.search(db, ws, doc_id=q)]


@router.post("/workspaces/{ws}/documents", status_code=201, response_model=DocumentRevisionDTO)
@router.post("/workspaces/{ws}/documents/", status_code=201, include_in_schema=False)
def create(ws: str, body: dict,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    doc_id = body.get("reference", "")
    title = body.get("title", "")
    rev = svc.create_document(db, ws, doc_id, title, current_user.login)
    return _doc_to_dict(db, rev, current_user.login)
