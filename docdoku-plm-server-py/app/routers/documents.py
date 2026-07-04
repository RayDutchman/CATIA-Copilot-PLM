"""文档端点路由（DocumentsResource + DocumentResource）。"""
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.document_service import DocumentService

router = APIRouter()
svc = DocumentService()


def _doc_to_dict(rev):
    return {
        "id": rev.documentmaster_id,
        "version": rev.version,
        "workspaceId": rev.workspace_id,
        "title": rev.title,
        "description": rev.description,
        "status": {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}.get(rev.status, "WIP"),
        "creationDate": str(rev.creation_date) if rev.creation_date else None,
        "checkOutUser": {"login": rev.checkout_user_login} if rev.checkout_user_login else None,
        "lastIteration": rev.last_iteration_number,
        "tags": [],
    }


def _split_doc_key(doc_key: str) -> tuple[str, str]:
    m = re.match(r'^(.+)-([A-Z]+)$', doc_key)
    if not m:
        raise HTTPException(400, f"Invalid doc key format: {doc_key}")
    return m.group(1), m.group(2)


@router.get("/workspaces/{ws}/documents/count")
def count(ws: str, current_user: Account = Depends(get_current_user),
          db: Session = Depends(get_db)):
    return {"count": svc.count_documents(db, ws)}


@router.get("/workspaces/{ws}/documents/search")
def search(ws: str, q: str = Query(""),
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    return svc.search(db, ws, title=q)


@router.get("/workspaces/{ws}/documents")
def list_docs(ws: str, start: int = Query(0, ge=0),
              max: int = Query(50, ge=1, le=500),
              length: int = Query(None, ge=1, le=500),
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    limit = length or max  # 兼容 Payara 前端 `max` 参数
    return [_doc_to_dict(r) for r in svc.list_revisions(db, ws, start, limit)]


@router.get("/workspaces/{ws}/documents/checkedout")
def list_checked_out(ws: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    return svc.list_checked_out(db, ws)


@router.get("/workspaces/{ws}/documents/countCheckedOut")
def count_checked_out(ws: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    return {"count": svc.count_checked_out_documents(db, ws)}


@router.get("/workspaces/{ws}/documents/doc_revs")
def search_doc_revs(ws: str, q: str = Query(""),
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return svc.search(db, ws, doc_id=q)


@router.post("/workspaces/{ws}/documents", status_code=201)
@router.post("/workspaces/{ws}/documents/", status_code=201, include_in_schema=False)
def create(ws: str, body: dict,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    doc_id = body.get("reference", "")
    title = body.get("title", "")
    rev = svc.create_document(db, ws, doc_id, title, current_user.login)
    return {"id": rev.documentmaster_id, "version": rev.version,
            "workspaceId": rev.workspace_id, "title": rev.title,
            "status": "WIP", "checkOutUser": {"login": rev.checkout_user_login}}


@router.get("/workspaces/{ws}/documents/{doc_key}")
def get_doc(ws: str, doc_key: str,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(svc.get_revision(db, ws, doc_id, ver))


@router.delete("/workspaces/{ws}/documents/{doc_key}", status_code=204)
def delete(ws: str, doc_key: str,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    svc.delete_revision(db, ws, doc_id, ver, current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/checkout")
def checkout(ws: str, doc_key: str,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(svc.checkout(db, ws, doc_id, ver, current_user.login))


@router.put("/workspaces/{ws}/documents/{doc_key}/checkin")
def checkin(ws: str, doc_key: str,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(svc.checkin(db, ws, doc_id, ver, current_user.login))


@router.put("/workspaces/{ws}/documents/{doc_key}/undocheckout")
def undo_checkout(ws: str, doc_key: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(svc.undo_checkout(db, ws, doc_id, ver, current_user.login))


@router.put("/workspaces/{ws}/documents/{doc_key}/release")
def release(ws: str, doc_key: str,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(svc.release(db, ws, doc_id, ver, current_user.login))


@router.put("/workspaces/{ws}/documents/{doc_key}/obsolete")
def obsolete(ws: str, doc_key: str,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(svc.mark_obsolete(db, ws, doc_id, ver, current_user.login))


@router.put("/workspaces/{ws}/documents/{doc_key}/newVersion")
def new_version(ws: str, doc_key: str,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(svc.create_new_version(db, ws, doc_id, ver, current_user.login))


@router.put("/workspaces/{ws}/documents/{doc_key}/tags")
def set_tags(ws: str, doc_key: str, body: dict,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.set_tags(db, ws, doc_id, ver, body.get("tags", []))


@router.post("/workspaces/{ws}/documents/{doc_key}/tags")
def add_tag(ws: str, doc_key: str, body: dict,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.add_tag(db, ws, doc_id, ver, body.get("tag", ""))


@router.delete("/workspaces/{ws}/documents/{doc_key}/tags/{tag_label}")
def remove_tag(ws: str, doc_key: str, tag_label: str,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.remove_tag(db, ws, doc_id, ver, tag_label)
