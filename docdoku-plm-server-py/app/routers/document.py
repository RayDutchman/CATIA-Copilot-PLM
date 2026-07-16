"""单个文档 CRUD（DocumentResource）。"""
import hashlib
import re
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.document_manager import DocumentService
from app.services.notification_manager import notification_service
from app.services.factory.acl_factory import check_write_access, parse_acl_entries
from app.schemas.document import DocumentRevisionDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = DocumentService()


def _split_doc_key(doc_key: str) -> tuple[str, str]:
    m = re.match(r'^(.+)-([A-Z]+)$', doc_key)
    if not m:
        raise HTTPException(400, f"Invalid doc key format: {doc_key}")
    return m.group(1), m.group(2)


@router.get("/workspaces/{ws}/documents/{doc_key}", response_model=DocumentRevisionDTO)
@router.get("/workspaces/{ws}/documents/{doc_key}/", include_in_schema=False)
def get_doc(ws: str, doc_key: str,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.build_revision_dto(db, svc.get_revision(db, ws, doc_id, ver), current_user.login)


@router.delete("/workspaces/{ws}/documents/{doc_key}", status_code=204)
@router.delete("/workspaces/{ws}/documents/{doc_key}/", status_code=204, include_in_schema=False)
def delete(ws: str, doc_key: str,
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    svc.delete_revision(db, ws, doc_id, ver, current_user.login)


@router.get("/workspaces/{ws}/documents/{doc_key}/aborted-workflows")
@router.get("/workspaces/{ws}/documents/{doc_key}/aborted-workflows/", include_in_schema=False)
def aborted_workflows(ws: str, doc_key: str,
                      db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.get_aborted_workflows(db, ws, doc_id, ver)


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-document-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-document-link/", include_in_schema=False)
def inverse_doc_link(ws: str, doc_key: str, iteration: int,
                     db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.get_inverse_document_links(db, ws, doc_id, ver, current_user.login)


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-part-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-part-link/", include_in_schema=False)
def inverse_part_link(ws: str, doc_key: str, iteration: int,
                      db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.get_inverse_part_links(db, ws, doc_id, ver)


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-product-instances-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-product-instances-link/", include_in_schema=False)
def inverse_product_link(ws: str, doc_key: str, iteration: int,
                         db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.get_inverse_product_links(db, ws, doc_id, ver)


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-path-data-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-path-data-link/", include_in_schema=False)
def inverse_path_link(ws: str, doc_key: str, iteration: int,
                      db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.get_inverse_path_links(db, ws, doc_id, ver)


@router.put("/workspaces/{ws}/documents/{doc_key}/iterations/{doc_iter}")
@router.put("/workspaces/{ws}/documents/{doc_key}/iterations/{doc_iter}/", include_in_schema=False)
def update_iteration(ws: str, doc_key: str, doc_iter: int, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    rev = svc.update_iteration(db, ws, doc_id, ver, doc_iter, body,
                               user_login=current_user.login)
    return svc.build_iteration_dto_after_update(db, rev, doc_iter, current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/checkout", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/checkout/", include_in_schema=False)
def checkout(ws: str, doc_key: str,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    svc._ensure_last_revision(db, ws, doc_id, ver)
    return svc.build_revision_dto(db, svc.checkout(db, ws, doc_id, ver, current_user.login), current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/checkin", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/checkin/", include_in_schema=False)
def checkin(ws: str, doc_key: str,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.build_revision_dto(db, svc.checkin(db, ws, doc_id, ver, current_user.login), current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/undocheckout", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/undocheckout/", include_in_schema=False)
def undo_checkout(ws: str, doc_key: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.build_revision_dto(db, svc.undo_checkout(db, ws, doc_id, ver, current_user.login), current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/release", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/release/", include_in_schema=False)
def release(ws: str, doc_key: str,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.build_revision_dto(db, svc.release(db, ws, doc_id, ver, current_user.login), current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/obsolete", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/obsolete/", include_in_schema=False)
def obsolete(ws: str, doc_key: str,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.build_revision_dto(db, svc.mark_obsolete(db, ws, doc_id, ver, current_user.login), current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/newVersion")
@router.put("/workspaces/{ws}/documents/{doc_key}/newVersion/", include_in_schema=False)
def new_version(ws: str, doc_key: str, body: dict = {},
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    title = body.get("title")
    description = body.get("description")
    workflow_model_id = body.get("workflowModelId")
    acl = body.get("acl", {})
    user_entries = parse_acl_entries(acl.get("userEntries")) if acl else None
    user_group_entries = parse_acl_entries(acl.get("groupEntries")) if acl else None
    role_mapping = body.get("roleMapping")
    user_role_mapping = {}
    group_role_mapping = {}
    if role_mapping:
        for rm in role_mapping:
            role_name = rm.get("roleName", "")
            if role_name:
                user_role_mapping[role_name] = rm.get("userLogins", [])
                group_role_mapping[role_name] = rm.get("groupIds", [])
    old_rev = svc.get_revision(db, ws, doc_id, ver)
    new_rev = svc.create_new_version(db, ws, doc_id, ver, current_user.login,
                                     title=title, description=description,
                                     workflow_model_id=workflow_model_id,
                                     user_entries=user_entries,
                                     user_group_entries=user_group_entries,
                                     user_role_mapping=user_role_mapping,
                                     group_role_mapping=group_role_mapping)
    old_dict = svc.build_revision_dto(db, old_rev, current_user.login)
    new_dict = svc.build_revision_dto(db, new_rev, current_user.login)
    return [old_dict, new_dict]


@router.put("/workspaces/{ws}/documents/{doc_key}/tags")
@router.put("/workspaces/{ws}/documents/{doc_key}/tags/", include_in_schema=False)
def set_tags(ws: str, doc_key: str, body: dict,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    raw_tags = body.get("tags", [])
    if raw_tags and isinstance(raw_tags[0], dict):
        labels = [t.get("label", "") for t in raw_tags if t.get("label")]
    else:
        labels = raw_tags
    svc.set_tags(db, ws, doc_id, ver, labels, current_user.login)
    return svc.build_revision_dto(db, svc.get_revision(db, ws, doc_id, ver), current_user.login)


@router.post("/workspaces/{ws}/documents/{doc_key}/tags")
@router.post("/workspaces/{ws}/documents/{doc_key}/tags/", include_in_schema=False)
def add_tag(ws: str, doc_key: str, body: dict,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    raw_tags = body.get("tags", [])
    if raw_tags and isinstance(raw_tags[0], dict):
        new_labels = [t.get("label", "") for t in raw_tags if t.get("label")]
    else:
        new_labels = raw_tags
    if not new_labels:
        return svc.build_revision_dto(db, svc.get_revision(db, ws, doc_id, ver), current_user.login)
    svc.add_tags(db, ws, doc_id, ver, new_labels, current_user.login)
    return svc.build_revision_dto(db, svc.get_revision(db, ws, doc_id, ver), current_user.login)


@router.delete("/workspaces/{ws}/documents/{doc_key}/tags/{tag_label}")
@router.delete("/workspaces/{ws}/documents/{doc_key}/tags/{tag_label}/", include_in_schema=False)
def remove_tag(ws: str, doc_key: str, tag_label: str,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return svc.remove_tag(db, ws, doc_id, ver, tag_label, current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/acl", status_code=204)
@router.put("/workspaces/{ws}/documents/{doc_key}/acl/", status_code=204, include_in_schema=False)
def update_doc_acl(ws: str, doc_key: str, body: dict,
                   db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    doc_id, version = _split_doc_key(doc_key)
    svc.update_acl(db, ws, doc_id, version, current_user.login, body)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/documents/{doc_key}/move", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/move/", include_in_schema=False)
def move_document(ws: str, doc_key: str, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    folder_path = body.get("path", "")
    return svc.build_revision_dto(db, svc.move_document(db, ws, doc_id, ver, folder_path, current_user.login), current_user.login)


@router.get("/workspaces/{ws}/documents/{doc_key}/share")
@router.get("/workspaces/{ws}/documents/{doc_key}/share/", include_in_schema=False)
def get_share(ws: str, doc_key: str,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    rev = svc.get_revision(db, ws, doc_id, ver)
    return {"publicShared": getattr(rev, "public_shared", False)}


@router.post("/workspaces/{ws}/documents/{doc_key}/share", status_code=201)
@router.post("/workspaces/{ws}/documents/{doc_key}/share/", status_code=201, include_in_schema=False)
def share_document(ws: str, doc_key: str,
                   body: dict = Body({}),
                   current_user: Account = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    svc.get_revision(db, ws, doc_id, ver)
    from app.models.part import SharedEntity
    shared_uuid = str(uuid.uuid4())
    password = body.get("password")
    expire_date_str = body.get("expireDate")
    from app.services.share_manager import share_manager
    shared_uuid = share_manager.create_shared_document(
        db, ws, doc_id, ver, current_user.login, password, expire_date_str
    )
    return {"uuid": shared_uuid, "workspaceId": ws}


@router.put("/workspaces/{ws}/documents/{doc_key}/publish", status_code=204)
@router.put("/workspaces/{ws}/documents/{doc_key}/publish/", status_code=204, include_in_schema=False)
def publish(ws: str, doc_key: str,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    svc.set_public_shared(db, ws, doc_id, ver, True, current_user.login)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/documents/{doc_key}/unpublish", status_code=204)
@router.put("/workspaces/{ws}/documents/{doc_key}/unpublish/", status_code=204, include_in_schema=False)
def unpublish(ws: str, doc_key: str,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    svc.set_public_shared(db, ws, doc_id, ver, False, current_user.login)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/subscribe", status_code=204)
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/subscribe/", status_code=204, include_in_schema=False)
def subscribe_iteration_change(ws: str, doc_key: str,
                               current_user: Account = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    notification_service.subscribe_iteration_change(db, ws, doc_id, ver, current_user.login)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/unsubscribe", status_code=204)
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/unsubscribe/", status_code=204, include_in_schema=False)
def unsubscribe_iteration_change(ws: str, doc_key: str,
                                 current_user: Account = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    notification_service.unsubscribe_iteration_change(db, ws, doc_id, ver, current_user.login)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/subscribe", status_code=204)
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/subscribe/", status_code=204, include_in_schema=False)
def subscribe_state_change(ws: str, doc_key: str,
                           current_user: Account = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    notification_service.subscribe_state_change(db, ws, doc_id, ver, current_user.login)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/unsubscribe", status_code=204)
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/unsubscribe/", status_code=204, include_in_schema=False)
def unsubscribe_state_change(ws: str, doc_key: str,
                             current_user: Account = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    notification_service.unsubscribe_state_change(db, ws, doc_id, ver, current_user.login)
    return Response(status_code=204)


@router.delete("/workspaces/{ws}/documents/{doc_key}/iterations/{doc_iter}/files/{file_name}", status_code=204)
@router.delete("/workspaces/{ws}/documents/{doc_key}/iterations/{doc_iter}/files/{file_name}/", status_code=204, include_in_schema=False)
def remove_doc_file(ws: str, doc_key: str, doc_iter: int, file_name: str,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    svc.delete_document_file(db, ws, doc_id, ver, doc_iter, file_name, current_user.login)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/documents/{doc_key}/iterations/{doc_iter}/files/{file_name}")
@router.put("/workspaces/{ws}/documents/{doc_key}/iterations/{doc_iter}/files/{file_name}/", include_in_schema=False)
def rename_doc_file(ws: str, doc_key: str, doc_iter: int, file_name: str,
                    body: dict = Body(...),
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    new_file_name = body.get("fileName")
    if not new_file_name:
        raise HTTPException(400, "fileName is required")
    return svc.rename_document_file(db, ws, doc_id, ver, doc_iter, file_name, new_file_name, current_user.login)
