"""文档集合路由（DocumentsResource）。"""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.document_manager import DocumentService
from app.schemas.document import DocumentRevisionDTO
from app.services.factory.acl_factory import parse_acl_entries

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
            revisions = svc.resolve_es_document_keys(db, ws, keys)
            return [svc.build_revision_dto(db, dr, current_user.login) for dr in revisions]
    except Exception:
        pass  # ES 失败 → fallback

    # DB LIKE fallback
    docs = svc.search_documents_sql(
        db, ws, q=q, doc_id=id, title=title, version=version,
        author=author, tags=tags, content=content,
        createdFrom=createdFrom, createdTo=createdTo,
        modifiedFrom=modifiedFrom, modifiedTo=modifiedTo,
        start=start, size=size,
    )
    return [svc.build_revision_dto(db, d, current_user.login) for d in docs]


@router.get("/workspaces/{ws}/documents", response_model=List[DocumentRevisionDTO])
@router.get("/workspaces/{ws}/documents/", include_in_schema=False)
def list_docs(ws: str, start: int = Query(0, ge=0),
              max: int = Query(50, ge=1, le=500),
              length: int = Query(None, ge=1, le=500),
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    limit = length or max
    return [svc.build_revision_dto(db, r, current_user.login) for r in svc.list_revisions(db, ws, start, limit)]


@router.get("/workspaces/{ws}/documents/checkedout", response_model=List[DocumentRevisionDTO])
@router.get("/workspaces/{ws}/documents/checkedout/", include_in_schema=False)
def list_checked_out(ws: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    return [svc.build_revision_dto(db, r, current_user.login) for r in svc.list_checked_out(db, ws)]


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
    return [svc.build_revision_dto(db, r, current_user.login)
            for r in svc.search(db, ws, doc_id=q)]


@router.post("/workspaces/{ws}/documents", status_code=201, response_model=DocumentRevisionDTO)
@router.post("/workspaces/{ws}/documents/", status_code=201, include_in_schema=False)
def create(ws: str, body: dict,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    doc_id = body.get("reference", "")
    title = body.get("title", "")
    description = body.get("description", "")
    template_id = body.get("templateId")
    workflow_model_id = body.get("workflowModelId")
    acl = body.get("acl", {})
    role_mapping = body.get("roleMapping")
    rev = svc.create_document(db, ws, doc_id, title, current_user.login,
                               template_id=template_id,
                               workflow_model_id=workflow_model_id,
                               role_mapping=role_mapping,
                               description=description or None,
                               user_entries=parse_acl_entries(acl.get("userEntries")) if acl else None,
                               user_group_entries=parse_acl_entries(acl.get("groupEntries")) if acl else None)
    return svc.build_revision_dto(db, rev, current_user.login)
