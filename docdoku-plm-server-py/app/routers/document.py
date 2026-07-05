"""单个文档 CRUD（DocumentResource）。"""
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.document_manager import DocumentService
from app.services.acl_helper import apply_acl

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = DocumentService()


def _split_doc_key(doc_key: str) -> tuple[str, str]:
    m = re.match(r'^(.+)-([A-Z]+)$', doc_key)
    if not m:
        raise HTTPException(400, f"Invalid doc key format: {doc_key}")
    return m.group(1), m.group(2)


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


@router.get("/workspaces/{ws}/documents/{doc_key}")
@router.get("/workspaces/{ws}/documents/{doc_key}/", include_in_schema=False)
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
@router.get("/workspaces/{ws}/documents/{doc_key}/aborted-workflows/", include_in_schema=False)
def aborted_workflows(ws: str, doc_key: str,
                      current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-document-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-document-link/", include_in_schema=False)
def inverse_doc_link(ws: str, doc_key: str, iteration: int,
                     current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-part-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-part-link/", include_in_schema=False)
def inverse_part_link(ws: str, doc_key: str, iteration: int,
                      current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-product-instances-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-product-instances-link/", include_in_schema=False)
def inverse_product_link(ws: str, doc_key: str, iteration: int,
                         current_user: Account = Depends(get_current_user)):
    return []


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-path-data-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-path-data-link/", include_in_schema=False)
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
@router.put("/workspaces/{ws}/documents/{doc_key}/checkout/", include_in_schema=False)
def checkout(ws: str, doc_key: str,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    svc._ensure_last_revision(db, ws, doc_id, ver)
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
@router.get("/workspaces/{ws}/documents/{doc_key}/share/", include_in_schema=False)
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
