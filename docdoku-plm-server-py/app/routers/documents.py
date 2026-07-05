"""文档端点路由（DocumentsResource + DocumentResource）。"""
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.document import DocumentRevision, DocumentMaster
from app.services.document_service import DocumentService
from app.services.acl_helper import apply_acl

router = APIRouter()
svc = DocumentService()


def _doc_to_dict(rev):
    iterations = []
    for it in (rev.iterations or []):
        it_dict = {
            "id": f"{rev.documentmaster_id}-{rev.version}-{it.iteration}",
            "iteration": it.iteration,
            "workspaceId": it.workspace_id,
            "documentMasterId": it.documentmaster_id,
            "documentRevisionVersion": it.documentrevision_version,
            "version": rev.version,
            "title": rev.title,
            "revisionNote": it.revision_note,
            "creationDate": str(it.creation_date) if it.creation_date else None,
            "modificationDate": str(it.modification_date) if it.modification_date else None,
            "checkInDate": str(it.check_in_date) if it.check_in_date else None,
            "instanceAttributes": [],
            "attachedFiles": [],
            "linkedDocuments": [],
            "author": {
                "login": it.author_login, "name": it.author_login,
                "email": None, "language": None, "workspaceId": it.workspace_id,
            },
            "documentRevision": {
                "id": f"{rev.documentmaster_id}-{rev.version}-{rev.version}",
                "workspaceId": rev.workspace_id,
                "version": rev.version,
                "documentMasterId": f"{rev.documentmaster_id}-{rev.version}",
                "status": None,
                "publicShared": False,
                "acl": None,
                "attributesLocked": False,
                "checkOutUser": None,
                "checkOutDate": None,
                "releaseAuthor": None,
                "releaseDate": None,
                "iterationSubscription": False,
                "stateSubscription": False,
                "commentLink": None,
            },
        }
        iterations.append(it_dict)
    dict_fields = {
        "id": f"{rev.documentmaster_id}-{rev.version}",
        "version": rev.version,
        "workspaceId": rev.workspace_id,
        "documentMasterId": rev.documentmaster_id,
        "title": rev.title,
        "description": rev.description,
        "status": {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}.get(rev.status, "WIP"),
        "creationDate": str(rev.creation_date) if rev.creation_date else None,
        "checkOutDate": str(rev.check_out_date) if rev.check_out_date else None,
        "releaseDate": str(rev.release_date) if rev.release_date else None,
        "obsoleteDate": str(rev.obsolete_date) if rev.obsolete_date else None,
        "lastIteration": rev.last_iteration_number,
        "documentIterations": iterations,
        "tags": [],
        "path": rev.location_completepath,
        "routePath": None,
        "acl": getattr(rev, "acl_id", None),
        "publicShared": False, "attributesLocked": False,
        "commentLink": None, "iterationSubscription": False,
        "stateSubscription": False,
        "releaseAuthor": None,
        "obsoleteAuthor": None,
        "type": rev.document_master.type if rev.document_master else None,
        "author": {
            "login": rev.author_login, "name": rev.author_login,
            "email": None, "language": None, "workspaceId": rev.workspace_id,
        },
    }
    if rev.checkout_user_login:
        dict_fields["checkOutUser"] = {
            "login": rev.checkout_user_login,
            "name": rev.checkout_user_login,
            "email": None,
            "language": None,
            "workspaceId": rev.checkout_user_workspace_id or rev.workspace_id,
        }
    if rev.release_user_login:
        dict_fields["releaseAuthor"] = {
            "login": rev.release_user_login, "name": rev.release_user_login or "",
            "email": None, "language": None, "workspaceId": rev.workspace_id,
        }
    if rev.obsolete_user_login:
        dict_fields["obsoleteAuthor"] = {
            "login": rev.obsolete_user_login, "name": rev.obsolete_user_login or "",
            "email": None, "language": None, "workspaceId": rev.workspace_id,
        }
    for k in ("description",):
        dict_fields.setdefault(k, "")
    return dict_fields


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
    query = db.query(DocumentRevision).join(
        DocumentMaster,
        (DocumentRevision.workspace_id == DocumentMaster.workspace_id) &
        (DocumentRevision.documentmaster_id == DocumentMaster.id)
    ).filter(DocumentMaster.workspace_id == ws)
    # 快速搜索: q 参数同时匹配 title 和 documentmaster_id
    if q:
        q_pattern = f"%{q}%"
        query = query.filter(or_(
            DocumentMaster.id.ilike(q_pattern),
            DocumentRevision.title.ilike(q_pattern),
        ))
    # 高级搜索各参数
    if id:
        query = query.filter(DocumentMaster.id.ilike(f"%{id}%"))
    if title:
        query = query.filter(DocumentRevision.title.ilike(f"%{title}%"))
    if version:
        query = query.filter(DocumentRevision.version == version)
    if author:
        query = query.filter(DocumentRevision.author_login == author)
    # MVP: tags 用子查询匹配（DB LIKE，ES 级搜索后续独立做）
    if tags:
        matched_ids = [row[0] for row in db.execute(sql_text(
            "SELECT dr.documentmaster_id FROM documentrevision dr "
            "JOIN documentrevision_tag t ON dr.documentmaster_id=t.documentmaster_id "
            "AND dr.version=t.documentrevision_version "
            "WHERE t.tag_label ILIKE :t AND dr.workspace_id=:w"
        ), {"t": f"%{tags}%", "w": ws}).fetchall()]
        query = query.filter(DocumentRevision.documentmaster_id.in_(matched_ids))
    # TODO: content / createdFrom~To / modifiedFrom~To / attributes 高级搜索
    # content: 搜索 DocumentIteration.revision_note 中的关键字
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
    # 日期范围过滤
    if createdFrom:
        query = query.filter(DocumentRevision.creation_date >= createdFrom)
    if createdTo:
        query = query.filter(DocumentRevision.creation_date <= createdTo)
    if modifiedFrom:
        from app.models.document import DocumentIteration as DI
        matched_ids = [row[0] for row in db.execute(sql_text(
            "SELECT DISTINCT di.documentmaster_id FROM documentiteration di "
            "WHERE di.workspace_id = :w AND di.modificationdate >= :d"
        ), {"w": ws, "d": modifiedFrom}).fetchall()]
        if matched_ids:
            query = query.filter(DocumentRevision.documentmaster_id.in_(matched_ids))
        else:
            query = query.filter(DocumentRevision.documentmaster_id == None)
    if modifiedTo:
        from app.models.document import DocumentIteration as DI
        matched_ids = [row[0] for row in db.execute(sql_text(
            "SELECT DISTINCT di.documentmaster_id FROM documentiteration di "
            "WHERE di.workspace_id = :w AND di.modificationdate <= :d"
        ), {"w": ws, "d": modifiedTo}).fetchall()]
        if matched_ids:
            query = query.filter(DocumentRevision.documentmaster_id.in_(matched_ids))
        else:
            query = query.filter(DocumentRevision.documentmaster_id == None)
    # attributes: 搜索 instanceAttributes（保留为爱可，前端可能不传）
    docs = query.order_by(DocumentMaster.id).offset(start).limit(size).all()
    return [_doc_to_dict(d) for d in docs]


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
    return [_doc_to_dict(r) for r in svc.list_checked_out(db, ws)]


@router.get("/workspaces/{ws}/documents/countCheckedOut")
def count_checked_out(ws: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    return {"count": svc.count_checked_out_documents(db, ws)}


@router.get("/workspaces/{ws}/documents/doc_revs")
def search_doc_revs(ws: str, q: str = Query(""),
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return [_doc_to_dict(r) for r in svc.search(db, ws, doc_id=q)]


@router.post("/workspaces/{ws}/documents", status_code=201)
@router.post("/workspaces/{ws}/documents/", status_code=201, include_in_schema=False)
def create(ws: str, body: dict,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    doc_id = body.get("reference", "")
    title = body.get("title", "")
    rev = svc.create_document(db, ws, doc_id, title, current_user.login)
    return _doc_to_dict(rev)


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


@router.get("/workspaces/{ws}/documents/{doc_key}/aborted-workflows")
def aborted_workflows(ws: str, doc_key: str,
                      current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-document-link")
def inverse_doc_link(ws: str, doc_key: str, iteration: int,
                     current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-part-link")
def inverse_part_link(ws: str, doc_key: str, iteration: int,
                      current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-product-instances-link")
def inverse_product_link(ws: str, doc_key: str, iteration: int,
                         current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-path-data-link")
def inverse_path_link(ws: str, doc_key: str, iteration: int,
                      current_user: Account = Depends(get_current_user)):
    return []


@router.put("/workspaces/{ws}/documents/{doc_key}/iterations/{doc_iter}")
@router.put("/workspaces/{ws}/documents/{doc_key}/iterations/{doc_iter}/", include_in_schema=False)
def update_iteration(ws: str, doc_key: str, doc_iter: int, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(svc.update_iteration(db, ws, doc_id, ver, doc_iter, body))


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


@router.put("/workspaces/{ws}/documents/{doc_key}/acl")
@router.put("/workspaces/{ws}/documents/{doc_key}/acl/", include_in_schema=False)
def update_doc_acl(ws: str, doc_key: str, body: dict,
                   db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    doc_id, version = _split_doc_key(doc_key)
    dr = svc.get_revision(db, ws, doc_id, version)
    acl_id = getattr(dr, "acl_id", None)
    new_acl_id = apply_acl(db, acl_id, body.get("userEntries", {}), body.get("groupEntries", {}))
    if dr.acl_id != new_acl_id:
        dr.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}


@router.put("/workspaces/{ws}/documents/{doc_key}/move")
@router.put("/workspaces/{ws}/documents/{doc_key}/move/", include_in_schema=False)
def move_document(ws: str, doc_key: str, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    folder_path = body.get("parentFolder", "")
    return _doc_to_dict(svc.move_document(db, ws, doc_id, ver, folder_path))


@router.get("/workspaces/{ws}/documents/{doc_key}/share")
def get_share(ws: str, doc_key: str,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    rev = svc.get_revision(db, ws, doc_id, ver)
    return {"publicShared": getattr(rev, "public_shared", False)}


@router.put("/workspaces/{ws}/documents/{doc_key}/publish")
@router.put("/workspaces/{ws}/documents/{doc_key}/publish/", include_in_schema=False)
def publish(ws: str, doc_key: str,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    return {"publicShared": True}


@router.put("/workspaces/{ws}/documents/{doc_key}/unpublish")
@router.put("/workspaces/{ws}/documents/{doc_key}/unpublish/", include_in_schema=False)
def unpublish(ws: str, doc_key: str,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    return {"publicShared": False}


@router.get("/workspaces/{ws}/document-baselines")
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
    result = []
    for r in rows:
        baseline_id = r[0]
        docs = db.execute(sql_text(
            "SELECT bd.target_documentmaster_id, bd.target_docrevision_version, bd.target_iteration "
            "FROM baselineddocument bd WHERE bd.documentcollection_id = "
            "(SELECT documentcollection_id FROM documentbaseline WHERE id = :bid) "
            "ORDER BY bd.target_documentmaster_id"
        ), {"bid": baseline_id}).fetchall()
        result.append({
            "id": baseline_id,
            "name": r[1] or "",
            "description": r[2] or "",
            "type": r[3],
            "creationDate": r[4].isoformat() + "Z" if r[4] else None,
            "author": {
                "login": r[5] or "",
                "name": r[5] or "",
                "workspaceId": r[6] or ws,
            },
            "baselinedDocuments": [
                {
                    "documentMasterId": d[0],
                    "version": d[1],
                    "iteration": d[2],
                } for d in docs
            ],
        })
    return result


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/subscribe")
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/subscribe/", include_in_schema=False)
def subscribe_iteration_change(ws: str, doc_key: str,
                                current_user: Account = Depends(get_current_user)):
    return {"status": "ok"}


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/unsubscribe")
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/unsubscribe/", include_in_schema=False)
def unsubscribe_iteration_change(ws: str, doc_key: str,
                                  current_user: Account = Depends(get_current_user)):
    return {"status": "ok"}


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/subscribe")
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/subscribe/", include_in_schema=False)
def subscribe_state_change(ws: str, doc_key: str,
                            current_user: Account = Depends(get_current_user)):
    return {"status": "ok"}


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/unsubscribe")
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/unsubscribe/", include_in_schema=False)
def unsubscribe_state_change(ws: str, doc_key: str,
                              current_user: Account = Depends(get_current_user)):
    return {"status": "ok"}
