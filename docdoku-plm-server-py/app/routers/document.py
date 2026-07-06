"""单个文档 CRUD（DocumentResource）。"""
import re
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.security import ACL, AclUserEntry, AclUserGroupEntry
from app.services.document_manager import DocumentService
from app.services.acl_helper import apply_acl
from app.schemas.document import DocumentRevisionDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = DocumentService()


def _split_doc_key(doc_key: str) -> tuple[str, str]:
    m = re.match(r'^(.+)-([A-Z]+)$', doc_key)
    if not m:
        raise HTTPException(400, f"Invalid doc key format: {doc_key}")
    return m.group(1), m.group(2)


def _get_user_info(db, login, ws):
    """查 Account 表取真实 name/email/language。"""
    if not login:
        return {"login": "", "name": "", "email": None, "language": None, "workspaceId": ws or ""}
    acc = db.query(Account).filter(Account.login == login).first()
    return {
        "login": login,
        "name": acc.name if acc and acc.name else login,
        "email": acc.email if acc else None,
        "language": acc.language if acc else None,
        "workspaceId": ws or "",
    }


def _doc_to_dict(db, rev, current_user_login=None):
    _PERM_MAP = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}
    acl_id = getattr(rev, "acl_id", None)
    acl_data = None
    if acl_id and db:
        acl = db.query(ACL).filter(ACL.id == acl_id).first()
        if acl:
            user_entries = db.query(AclUserEntry).filter(AclUserEntry.acl_id == acl_id).all()
            group_entries = db.query(AclUserGroupEntry).filter(AclUserGroupEntry.acl_id == acl_id).all()
            acl_data = {
                "userEntries": [{"key": e.principal_login, "value": _PERM_MAP.get(e.permission, "FORBIDDEN")} for e in user_entries],
                "groupEntries": [{"key": e.principal_id, "value": _PERM_MAP.get(e.permission, "FORBIDDEN")} for e in group_entries],
                "userEntriesMap": {e.principal_login: _PERM_MAP.get(e.permission, "FORBIDDEN") for e in user_entries},
                "userGroupEntriesMap": {},
            }

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
            "author": _get_user_info(db, it.author_login, it.workspace_id),
            "documentRevision": {
                "id": f"{rev.documentmaster_id}-{rev.version}-{rev.version}",
                "workspaceId": rev.workspace_id,
                "version": rev.version,
                "documentMasterId": f"{rev.documentmaster_id}-{rev.version}",
                "status": None,
                "publicShared": False,
                "acl": acl_data or {},
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

    iter_sub = None
    state_sub = None
    if db and current_user_login:
        iter_sub = db.execute(sql_text(
            "SELECT 1 FROM iterationchangesubscription WHERE documentmaster_id=:did "
            "AND documentmaster_workspace_id=:ws AND documentrevision_version=:ver "
            "AND subscriber_login=:login AND subscriber_workspace_id=:sws LIMIT 1"
        ), {"did": rev.documentmaster_id, "ws": rev.workspace_id, "ver": rev.version,
            "login": current_user_login, "sws": rev.workspace_id}).scalar()
        state_sub = db.execute(sql_text(
            "SELECT 1 FROM statechangesubscription WHERE documentmaster_id=:did "
            "AND documentmaster_workspace_id=:ws AND documentrevision_version=:ver "
            "AND subscriber_login=:login AND subscriber_workspace_id=:sws LIMIT 1"
        ), {"did": rev.documentmaster_id, "ws": rev.workspace_id, "ver": rev.version,
            "login": current_user_login, "sws": rev.workspace_id}).scalar()

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
        "acl": acl_data or {},
        "publicShared": bool(getattr(rev, "public_shared", False)), "attributesLocked": False,
        "commentLink": None, "iterationSubscription": iter_sub is not None,
        "stateSubscription": state_sub is not None,
        "releaseAuthor": None,
        "obsoleteAuthor": None,
        "type": rev.document_master.type if rev.document_master else None,
        "author": _get_user_info(db, rev.author_login, rev.workspace_id),
    }
    if rev.checkout_user_login:
        dict_fields["checkOutUser"] = _get_user_info(
            db, rev.checkout_user_login,
            rev.checkout_user_workspace_id or rev.workspace_id,
        )
    if rev.release_user_login:
        dict_fields["releaseAuthor"] = _get_user_info(
            db, rev.release_user_login, rev.workspace_id,
        )
    if rev.obsolete_user_login:
        dict_fields["obsoleteAuthor"] = _get_user_info(
            db, rev.obsolete_user_login, rev.workspace_id,
        )
    for k in ("description",):
        dict_fields.setdefault(k, "")
    # 计算 lifeCycleState（来自关联的 workflow）
    wf_id = getattr(rev, "workflow_id", None)
    if wf_id and db:
        wf_row = db.execute(sql_text(
            "SELECT id, finallifecyclestate FROM workflow WHERE id=:wid"
        ), {"wid": wf_id}).first()
        if wf_row:
            act = db.execute(sql_text(
                "SELECT lifecyclestate FROM activity "
                "WHERE workflow_id=:wid AND dtype!='org.docdoku.plm.server.core.workflow.ParallelActivity' "
                "ORDER BY step ASC"
            ), {"wid": wf_id}).first()
            lcs = act[0] if act else wf_row[1]
            dict_fields["lifeCycleState"] = lcs
    dict_fields.setdefault("lifeCycleState", None)
    # 查询标签
    if db:
        tag_rows = db.execute(sql_text(
            "SELECT tag_label FROM documentrevision_tag "
            "WHERE documentmaster_workspace_id=:ws AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"
        ), {"ws": rev.workspace_id, "did": rev.documentmaster_id, "ver": rev.version}).fetchall()
        dict_fields["tags"] = [tr[0] for tr in tag_rows]
    return dict_fields


@router.get("/workspaces/{ws}/documents/{doc_key}", response_model=DocumentRevisionDTO)
@router.get("/workspaces/{ws}/documents/{doc_key}/", include_in_schema=False)
def get_doc(ws: str, doc_key: str,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(db, svc.get_revision(db, ws, doc_id, ver), current_user.login)


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
    rev = svc.get_revision(db, ws, doc_id, ver)
    workflow_id = getattr(rev, "workflow_id", None)
    if not workflow_id:
        return []
    rows = db.execute(sql_text(
        "SELECT id, aborteddate, finallifecyclestate FROM workflow WHERE id=:wid AND aborteddate IS NOT NULL"
    ), {"wid": workflow_id}).fetchall()
    result = []
    for r in rows:
        activities = db.execute(sql_text(
            "SELECT step, dtype, lifecyclestate, taskstocomplete FROM activity "
            "WHERE workflow_id=:wid ORDER BY step ASC"
        ), {"wid": r[0]}).fetchall()
        activity_list = []
        for a in activities:
            tasks = db.execute(sql_text(
                "SELECT num, title, instructions, status, worker_login, "
                "worker_workspace_id, duration, signature, closuredate, "
                "closurecomment, startdate, targetiteration "
                "FROM task WHERE workflow_id=:wid AND activity_step=:step "
                "ORDER BY num ASC"
            ), {"wid": r[0], "step": a[0]}).fetchall()
            task_list = []
            for t in tasks:
                worker = None
                if t[4]:
                    worker = _get_user_info(db, t[4], t[5] or ws)
                task_list.append({
                    "num": t[0],
                    "title": t[1],
                    "instructions": t[2],
                    "status": t[3],
                    "worker": worker,
                    "duration": t[6],
                    "signature": t[7],
                    "closureDate": str(t[8]) if t[8] else None,
                    "closureComment": t[9],
                    "startDate": str(t[10]) if t[10] else None,
                    "targetIteration": t[11],
                })
            activity_list.append({
                "step": a[0],
                "type": a[1],
                "lifeCycleState": a[2],
                "tasksToComplete": a[3],
                "tasks": task_list,
            })
        result.append({
            "id": r[0],
            "abortedDate": str(r[1]) if r[1] else None,
            "finalLifeCycleState": r[2],
            "activities": activity_list,
        })
    return result


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-document-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-document-link/", include_in_schema=False)
def inverse_doc_link(ws: str, doc_key: str, iteration: int,
                     db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    doc_id, ver = _split_doc_key(doc_key)
    rows = db.execute(sql_text(
        "SELECT di.workspace_id, di.documentmaster_id, di.documentrevision_version, "
        "di.iteration, dl.id AS link_id, dl.target_documentmaster_id, "
        "dl.target_docrevision_version, dl.target_workspace_id, dl.commentdata "
        "FROM documentiteration_documentlink didl "
        "JOIN documentlink dl ON didl.documentlink_id = dl.id "
        "JOIN documentiteration di ON "
        "di.workspace_id=didl.workspace_id AND di.documentmaster_id=didl.documentmaster_id "
        "AND di.documentrevision_version=didl.documentrevision_version "
        "AND di.iteration=didl.iteration "
        "WHERE dl.target_workspace_id=:ws AND dl.target_documentmaster_id=:did "
        "AND dl.target_docrevision_version=:ver"
    ), {"ws": ws, "did": doc_id, "ver": ver}).fetchall()
    # 去重，返回源文档的完整 DTO
    seen = set()
    result = []
    for r in rows:
        key = (r[0], r[1], r[2])
        if key in seen:
            continue
        seen.add(key)
        rev = svc.get_revision(db, r[0], r[1], r[2])
        result.append(_doc_to_dict(db, rev, current_user.login))
    return result


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-part-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-part-link/", include_in_schema=False)
def inverse_part_link(ws: str, doc_key: str, iteration: int,
                      db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    doc_id, ver = _split_doc_key(doc_key)
    rows = db.execute(sql_text(
        "SELECT pi.workspace_id, pi.partmaster_partnumber, pi.partrevision_version, "
        "pi.iteration, dl.id AS link_id, dl.target_documentmaster_id, "
        "dl.target_docrevision_version, dl.target_workspace_id "
        "FROM partiteration_documentlink pidl "
        "JOIN documentlink dl ON pidl.documentlink_id = dl.id "
        "JOIN partiteration pi ON "
        "pi.workspace_id=pidl.workspace_id AND pi.partmaster_partnumber=pidl.partmaster_partnumber "
        "AND pi.partrevision_version=pidl.partrevision_version AND pi.iteration=pidl.iteration "
        "WHERE dl.target_workspace_id=:ws AND dl.target_documentmaster_id=:did "
        "AND dl.target_docrevision_version=:ver"
    ), {"ws": ws, "did": doc_id, "ver": ver}).fetchall()
    from app.services.product_manager import ProductService
    from app.services.part_mapper import map_revision
    psvc = ProductService()
    seen = set()
    result = []
    for r in rows:
        key = (r[0], r[1], r[2])
        if key in seen:
            continue
        seen.add(key)
        pr = psvc.get_revision(db, r[0], r[1], r[2])
        result.append(map_revision(pr, db).model_dump())
    return result


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-product-instances-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-product-instances-link/", include_in_schema=False)
def inverse_product_link(ws: str, doc_key: str, iteration: int,
                         db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    doc_id, ver = _split_doc_key(doc_key)
    rows = db.execute(sql_text(
        "SELECT DISTINCT pii.workspace_id, pii.serialnumber, "
        "pii.instanceiteration, pii.ci_updatebranchid "
        "FROM prdinstiteration_documentlink pidl "
        "JOIN documentlink dl ON pidl.documentlink_id = dl.id "
        "JOIN prdinstiteration pii ON "
        "pii.workspace_id=pidl.workspace_id AND pii.serialnumber=pidl.productinstanceserial "
        "AND pii.instanceiteration=pidl.productinstance_iteration "
        "AND pii.ci_updatebranchid=pidl.ci_updatebranchid "
        "WHERE dl.target_workspace_id=:ws AND dl.target_documentmaster_id=:did "
        "AND dl.target_docrevision_version=:ver"
    ), {"ws": ws, "did": doc_id, "ver": ver}).fetchall()
    result = []
    for r in rows:
        # 查询产品实例主数据
        pinst = db.execute(sql_text(
            "SELECT pi.id, pi.serialnumber, pi.productmaster_id, "
            "pii.instanceiteration, pii.iterationnote, pii.creationdate, "
            "pii.author_login, pii.author_workspace_id "
            "FROM productinstance pi "
            "JOIN prdinstiteration pii ON pi.id=pii.productinstance_id "
            "AND pii.instanceiteration=:iter AND pii.ci_updatebranchid=:br "
            "WHERE pi.workspace_id=:ws AND pi.serialnumber=:sn"
        ), {"ws": r[0], "sn": r[1], "iter": r[2], "br": r[3]}).fetchone()
        if pinst:
            result.append({
                "id": pinst[0], "serialNumber": pinst[1],
                "productMasterId": pinst[2],
                "instanceIteration": pinst[3],
                "iterationNote": pinst[4] or "",
                "creationDate": str(pinst[5]) if pinst[5] else None,
                "author": _get_user_info(db, pinst[6], pinst[7] or ws),
                "workspaceId": r[0],
            })
        else:
            result.append({
                "workspaceId": r[0], "serialNumber": r[1],
                "instanceIteration": r[2], "ciUpdateBranchId": r[3],
            })
    return result


@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-path-data-link")
@router.get("/workspaces/{ws}/documents/{doc_key}/{iteration}/inverse-path-data-link/", include_in_schema=False)
def inverse_path_link(ws: str, doc_key: str, iteration: int,
                      db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    doc_id, ver = _split_doc_key(doc_key)
    rows = db.execute(sql_text(
        "SELECT DISTINCT pd.id AS path_data_id, pd.path, pdi.workspace_id, "
        "pdi.productconfig_master_id, pdi.iteration "
        "FROM pathdataiteration_documentlink pdl "
        "JOIN documentlink dl ON pdl.documentlink_id = dl.id "
        "JOIN pathdataiteration pdi ON "
        "pdi.workspace_id=pdl.workspace_id AND pdi.id=pdl.pathdataiteration_id "
        "JOIN pathdata pd ON pd.id = pdi.pathdata_id "
        "WHERE dl.target_workspace_id=:ws AND dl.target_documentmaster_id=:did "
        "AND dl.target_docrevision_version=:ver"
    ), {"ws": ws, "did": doc_id, "ver": ver}).fetchall()
    result = []
    for r in rows:
        result.append({
            "pathDataId": r[0], "path": r[1],
            "workspaceId": r[2], "productConfigMasterId": r[3],
            "iteration": r[4],
        })
    return result


@router.put("/workspaces/{ws}/documents/{doc_key}/iterations/{doc_iter}")
@router.put("/workspaces/{ws}/documents/{doc_key}/iterations/{doc_iter}/", include_in_schema=False)
def update_iteration(ws: str, doc_key: str, doc_iter: int, body: dict,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    rev = svc.update_iteration(db, ws, doc_id, ver, doc_iter, body)
    # 返回该迭代的 dict，不是整个 revision
    target_it = next((it for it in rev.iterations if it.iteration == doc_iter), None)
    if target_it is None:
        raise HTTPException(404, "Iteration not found after update")
    # 查询 attachedFiles
    attached_rows = db.execute(sql_text(
        "SELECT attachedfile_fullname FROM documentiteration_binres "
        "WHERE workspace_id=:ws AND documentmaster_id=:did "
        "AND documentrevision_version=:ver AND iteration=:iter"
    ), {"ws": ws, "did": doc_id, "ver": ver, "iter": doc_iter}).fetchall()
    attached_files = []
    for ar in attached_rows:
        from app.models.part import BinaryResource
        br = db.query(BinaryResource).filter(
            BinaryResource.full_name == ar[0]).first()
        if br:
            attached_files.append({
                "fullName": br.full_name,
                "contentLength": br.content_length or 0,
                "lastModified": str(br.last_modified) if br.last_modified else None,
            })
        else:
            attached_files.append({"fullName": ar[0]})
    # 查询 linkedDocuments
    linked_rows = db.execute(sql_text(
        "SELECT dl.id, dl.target_workspace_id, dl.target_documentmaster_id, "
        "dl.target_docrevision_version, dl.commentdata "
        "FROM documentiteration_documentlink didl "
        "JOIN documentlink dl ON didl.documentlink_id = dl.id "
        "WHERE didl.workspace_id=:ws AND didl.documentmaster_id=:did "
        "AND didl.documentrevision_version=:ver AND didl.iteration=:iter"
    ), {"ws": ws, "did": doc_id, "ver": ver, "iter": doc_iter}).fetchall()
    linked_documents = []
    for lr in linked_rows:
        try:
            linked_rev = svc.get_revision(db, lr[1], lr[2], lr[3])
            ld = _doc_to_dict(db, linked_rev, current_user.login)
            ld["commentLink"] = lr[4] or ""
            linked_documents.append(ld)
        except HTTPException:
            linked_documents.append({
                "workspaceId": lr[1], "documentMasterId": lr[2],
                "version": lr[3], "commentLink": lr[4] or "",
            })
    it_dict = {
        "id": f"{rev.documentmaster_id}-{rev.version}-{doc_iter}",
        "iteration": doc_iter,
        "workspaceId": rev.workspace_id,
        "documentMasterId": rev.documentmaster_id,
        "documentRevisionVersion": rev.version,
        "version": rev.version,
        "title": rev.title,
        "revisionNote": target_it.revision_note,
        "creationDate": str(target_it.creation_date) if target_it.creation_date else None,
        "modificationDate": str(target_it.modification_date) if target_it.modification_date else None,
        "checkInDate": str(target_it.check_in_date) if target_it.check_in_date else None,
        "instanceAttributes": [],
        "attachedFiles": attached_files,
        "linkedDocuments": linked_documents,
        "author": _get_user_info(db, target_it.author_login, target_it.workspace_id),
        "documentRevision": {
            "id": f"{rev.documentmaster_id}-{rev.version}-{rev.version}",
            "workspaceId": rev.workspace_id,
            "version": rev.version,
            "documentMasterId": f"{rev.documentmaster_id}-{rev.version}",
            "status": None, "publicShared": False, "acl": {},
            "attributesLocked": False, "checkOutUser": None,
            "checkOutDate": None, "releaseAuthor": None,
            "releaseDate": None, "iterationSubscription": False,
            "stateSubscription": False, "commentLink": None,
        },
    }
    return it_dict


@router.put("/workspaces/{ws}/documents/{doc_key}/checkout", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/checkout/", include_in_schema=False)
def checkout(ws: str, doc_key: str,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    svc._ensure_last_revision(db, ws, doc_id, ver)
    return _doc_to_dict(db, svc.checkout(db, ws, doc_id, ver, current_user.login), current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/checkin", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/checkin/", include_in_schema=False)
def checkin(ws: str, doc_key: str,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(db, svc.checkin(db, ws, doc_id, ver, current_user.login), current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/undocheckout", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/undocheckout/", include_in_schema=False)
def undo_checkout(ws: str, doc_key: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(db, svc.undo_checkout(db, ws, doc_id, ver, current_user.login), current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/release", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/release/", include_in_schema=False)
def release(ws: str, doc_key: str,
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(db, svc.release(db, ws, doc_id, ver, current_user.login), current_user.login)


@router.put("/workspaces/{ws}/documents/{doc_key}/obsolete", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/obsolete/", include_in_schema=False)
def obsolete(ws: str, doc_key: str,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    return _doc_to_dict(db, svc.mark_obsolete(db, ws, doc_id, ver, current_user.login), current_user.login)


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
    user_entries = acl.get("userEntriesMap") if acl else None
    user_group_entries = acl.get("userGroupEntriesMap") if acl else None
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
                                     user_group_entries=user_group_entries)
    old_dict = _doc_to_dict(db, old_rev, current_user.login)
    new_dict = _doc_to_dict(db, new_rev, current_user.login)
    return [old_dict, new_dict]


@router.put("/workspaces/{ws}/documents/{doc_key}/tags")
@router.put("/workspaces/{ws}/documents/{doc_key}/tags/", include_in_schema=False)
def set_tags(ws: str, doc_key: str, body: dict,
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    raw_tags = body.get("tags", [])
    # 兼容 Java TagListDTO 格式: {tags: [{label: "xx"}, ...]}
    if raw_tags and isinstance(raw_tags[0], dict):
        labels = [t.get("label", "") for t in raw_tags if t.get("label")]
    else:
        labels = raw_tags
    svc.set_tags(db, ws, doc_id, ver, labels)
    return _doc_to_dict(db, svc.get_revision(db, ws, doc_id, ver), current_user.login)


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
        return _doc_to_dict(db, svc.get_revision(db, ws, doc_id, ver), current_user.login)
    existing_rows = db.execute(sql_text(
        "SELECT tag_label FROM documentrevision_tag "
        "WHERE documentmaster_workspace_id=:ws AND documentmaster_id=:did "
        "AND documentrevision_version=:ver"
    ), {"ws": ws, "did": doc_id, "ver": ver}).fetchall()
    existing_labels = [r[0] for r in existing_rows]
    merged = list(dict.fromkeys(existing_labels + new_labels))
    svc.set_tags(db, ws, doc_id, ver, merged)
    return _doc_to_dict(db, svc.get_revision(db, ws, doc_id, ver), current_user.login)


@router.delete("/workspaces/{ws}/documents/{doc_key}/tags/{tag_label}")
@router.delete("/workspaces/{ws}/documents/{doc_key}/tags/{tag_label}/", include_in_schema=False)
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


@router.put("/workspaces/{ws}/documents/{doc_key}/move", response_model=DocumentRevisionDTO)
@router.put("/workspaces/{ws}/documents/{doc_key}/move/", include_in_schema=False)
def move_document(ws: str, doc_key: str, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    folder_path = body.get("path", "")
    return _doc_to_dict(db, svc.move_document(db, ws, doc_id, ver, folder_path), current_user.login)


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
    doc_id, ver = _split_doc_key(doc_key)
    dr = svc.get_revision(db, ws, doc_id, ver)
    dr.public_shared = True
    db.commit()
    return {"publicShared": True}


@router.put("/workspaces/{ws}/documents/{doc_key}/unpublish")
@router.put("/workspaces/{ws}/documents/{doc_key}/unpublish/", include_in_schema=False)
def unpublish(ws: str, doc_key: str,
              current_user: Account = Depends(get_current_user),
              db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    dr = svc.get_revision(db, ws, doc_id, ver)
    dr.public_shared = False
    db.commit()
    return {"publicShared": False}


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/subscribe")
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/subscribe/", include_in_schema=False)
def subscribe_iteration_change(ws: str, doc_key: str,
                                current_user: Account = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    db.execute(sql_text(
        "INSERT INTO iterationchangesubscription "
        "(documentmaster_id, documentrevision_version, documentmaster_workspace_id, "
        "subscriber_login, subscriber_workspace_id) "
        "VALUES (:did, :ver, :ws, :login, :sws) "
        "ON CONFLICT (documentmaster_id, documentrevision_version, "
        "documentmaster_workspace_id, subscriber_login, subscriber_workspace_id) "
        "DO NOTHING"),
        {"did": doc_id, "ver": ver, "ws": ws, "login": current_user.login, "sws": ws})
    db.commit()
    return {"status": "ok"}


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/unsubscribe")
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/iterationChange/unsubscribe/", include_in_schema=False)
def unsubscribe_iteration_change(ws: str, doc_key: str,
                                  current_user: Account = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    db.execute(sql_text(
        "DELETE FROM iterationchangesubscription "
        "WHERE documentmaster_id=:did AND documentrevision_version=:ver "
        "AND documentmaster_workspace_id=:ws AND subscriber_login=:login "
        "AND subscriber_workspace_id=:sws"),
        {"did": doc_id, "ver": ver, "ws": ws, "login": current_user.login, "sws": ws})
    db.commit()
    return {"status": "ok"}


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/subscribe")
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/subscribe/", include_in_schema=False)
def subscribe_state_change(ws: str, doc_key: str,
                            current_user: Account = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    db.execute(sql_text(
        "INSERT INTO statechangesubscription "
        "(documentmaster_id, documentrevision_version, documentmaster_workspace_id, "
        "subscriber_login, subscriber_workspace_id) "
        "VALUES (:did, :ver, :ws, :login, :sws) "
        "ON CONFLICT (documentmaster_id, documentrevision_version, "
        "documentmaster_workspace_id, subscriber_login, subscriber_workspace_id) "
        "DO NOTHING"),
        {"did": doc_id, "ver": ver, "ws": ws, "login": current_user.login, "sws": ws})
    db.commit()
    return {"status": "ok"}


@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/unsubscribe")
@router.put("/workspaces/{ws}/documents/{doc_key}/notification/stateChange/unsubscribe/", include_in_schema=False)
def unsubscribe_state_change(ws: str, doc_key: str,
                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    doc_id, ver = _split_doc_key(doc_key)
    db.execute(sql_text(
        "DELETE FROM statechangesubscription "
        "WHERE documentmaster_id=:did AND documentrevision_version=:ver "
        "AND documentmaster_workspace_id=:ws AND subscriber_login=:login "
        "AND subscriber_workspace_id=:sws"),
        {"did": doc_id, "ver": ver, "ws": ws, "login": current_user.login, "sws": ws})
    db.commit()
    return {"status": "ok"}
