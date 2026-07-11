from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotAllowedException
from app.models.auth import Account
from app.services.task_manager import task_service, STATUS_MAP
from app.schemas.workflow import (
    TaskWrapperDTO, TaskHolderPartDTO,
)
from app.schemas.document.document_revision import DocumentRevisionDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _parse_task_id(task_id: str):
    """解析 Java 复合 task ID: "workflowId-step-taskIndex" → (wf_id, step, num)"""
    if isinstance(task_id, int):
        return None, None, task_id  # 旧版单 int
    parts = task_id.split("-")
    if len(parts) == 3:
        try:
            return int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            return None, None, task_id
    return None, None, task_id


def _doc_to_dict(db, rev, current_user_login=None):
    from app.routers.document import _doc_to_dict as _doc_full
    return _doc_full(db, rev, current_user_login)


def _part_to_dict(db: Session, rev):
    """转换 PartRevision 为 dict，author/checkOutUser 查 Account 表填充真实姓名。"""
    # 查 author 姓名
    author_acc = db.query(Account).filter(Account.login == rev.author_login).first() if rev.author_login else None
    author = {
        "login": rev.author_login or "",
        "name": (author_acc.name if author_acc and author_acc.name else rev.author_login) or "",
        "workspaceId": rev.workspace_id,
    }
    # 查 checkOutUser 姓名
    checkout_user = {}
    if rev.checkout_user_login:
        co_acc = db.query(Account).filter(Account.login == rev.checkout_user_login).first()
        checkout_user = {
            "login": rev.checkout_user_login,
            "name": (co_acc.name if co_acc and co_acc.name else rev.checkout_user_login) or "",
            "workspaceId": rev.workspace_id,
        }
    return {
        "partKey": f"{rev.partmaster_partnumber}-{rev.version}",
        "partNumber": rev.partmaster_partnumber,
        "version": rev.version,
        "name": rev.name or rev.partmaster_partnumber,
        "workspaceId": rev.workspace_id,
        "description": rev.description or "",
        "type": rev.part_master.type if rev.part_master else "",
        "status": {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}.get(rev.status, "WIP"),
        "checkOutUser": checkout_user,
        "checkOutDate": int(rev.check_out_date.timestamp() * 1000) if rev.check_out_date else None,
        "standardPart": rev.part_master.standard_part if rev.part_master else False,
        "author": author,
        "creationDate": int(rev.creation_date.timestamp() * 1000) if rev.creation_date else None,
    }


@router.get(f"{PREFIX}/tasks/{{login}}/assigned", response_model=List[TaskWrapperDTO])
@router.get(f"{PREFIX}/tasks/{{login}}/assigned/", include_in_schema=False)
def assigned_tasks(ws: str, login: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    return task_service.get_assigned_tasks(db, ws, login)


@router.get(f"{PREFIX}/tasks/{{task_id}}", response_model=TaskWrapperDTO)
@router.get(f"{PREFIX}/tasks/{{task_id}}/", include_in_schema=False)
def get_task(ws: str, task_id: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    wf_id, step, num = _parse_task_id(task_id)
    if wf_id is not None and step is not None:
        t = task_service.get_task(db, ws, workflow_id=wf_id,
                                       activity_step=step, task_num=num)
    else:
        t = task_service.get_task(db, ws, task_id=int(num) if isinstance(num, int) else num)
    # 查找 holder 信息
    _wf_id = t[11] if len(t) > 11 else None
    holder_type = None
    holder_reference = None
    holder_version = None
    if _wf_id:
        doc = db.execute(text(
            "SELECT documentmaster_id, version FROM documentrevision "
            "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
        ), {"wf_id": _wf_id, "ws": ws}).first()
        if doc:
            holder_type = "documents"
            holder_reference = doc[0]
            holder_version = doc[1]
        else:
            part = db.execute(text(
                "SELECT partmaster_partnumber, version FROM partrevision "
                "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
            ), {"wf_id": _wf_id, "ws": ws}).first()
            if part:
                holder_type = "part"
                holder_reference = part[0]
                holder_version = part[1]
            else:
                ww = db.execute(text(
                    "SELECT id FROM workspace_workflow "
                    "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
                ), {"wf_id": _wf_id, "ws": ws}).first()
                if ww:
                    holder_type = "workspace-workflow"
                    holder_reference = ww[0]
    # 查 worker 姓名
    _worker_login = t[13] if len(t) > 13 and t[13] else None
    _worker_ws = t[12] if len(t) > 12 else None
    if _worker_login:
        _worker_acc = db.query(Account).filter(Account.login == _worker_login).first()
        _worker = {
            "login": _worker_login,
            "name": (_worker_acc.name if _worker_acc and _worker_acc.name else _worker_login) or "",
            "workspaceId": _worker_ws,
        }
    else:
        _worker = {}
    return {
        "num": t[0],
        "title": t[9] if len(t) > 9 and t[9] else "",
        "instructions": t[4] if len(t) > 4 and t[4] else "",
        "status": STATUS_MAP.get(t[7], "NOT_STARTED"),
        "worker": _worker,
        "closureComment": t[1] if len(t) > 1 else None,
        "signature": t[5] if len(t) > 5 else None,
        "closureDate": t[2].isoformat() + "Z" if len(t) > 2 and t[2] else None,
        "holderType": holder_type,
        "holderReference": holder_reference,
        "holderVersion": holder_version,
        "workspaceId": ws,
        "workflowId": t[11] if len(t) > 11 else None,
        "activityStep": t[10] if len(t) > 10 else None,
    }


def _verify_downloaded(db: Session, ws: str, task_id: str, user_login: str):
    """检CTask：验证用户是否已检出/下载了关联的零件或文档。"""
    wf_id, step, num = _parse_task_id(task_id)
    if wf_id is None or step is None:
        t_info = db.execute(text(
            "SELECT workflow_id, activity_step FROM task WHERE num = :id LIMIT 1"
        ), {"id": num}).first()
        if not t_info:
            raise NotAllowedException("NotAllowedException42")
        wf_id, step = t_info[0], t_info[1]
    # 检查文档
    doc = db.execute(text(
        "SELECT dr.documentmaster_id, dr.version, dr.checkoutuser_login "
        "FROM documentrevision dr "
        "WHERE dr.workflow_id = :wf_id AND dr.workspace_id = :ws LIMIT 1"
    ), {"wf_id": wf_id, "ws": ws}).first()
    if doc:
        if doc[2] and doc[2] == user_login:
            return True
        raise NotAllowedException("NotAllowedException42")
    # 检查零件
    part = db.execute(text(
        "SELECT pr.partmaster_partnumber, pr.version, pr.checkoutuser_login "
        "FROM partrevision pr "
        "WHERE pr.workflow_id = :wf_id AND pr.workspace_id = :ws LIMIT 1"
    ), {"wf_id": wf_id, "ws": ws}).first()
    if part:
        if part[2] and part[2] == user_login:
            return True
        raise NotAllowedException("NotAllowedException42")
    return True


@router.put(f"{PREFIX}/tasks/{{task_id}}/check")
@router.put(f"{PREFIX}/tasks/{{task_id}}/check/", include_in_schema=False)
def check_task(ws: str, task_id: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    """checkTask：验证当前用户对关联文档/零件有下载权限。"""
    wf_id, step, num = _parse_task_id(task_id)
    if wf_id is not None and step is not None:
        if not task_service._is_potential_worker(
                db, ws, current_user.login, wf_id, step, num):
            raise NotAllowedException("NotAllowedException41")
    else:
        t_info = db.execute(text(
            "SELECT workflow_id, activity_step, num FROM task WHERE num = :id LIMIT 1"
        ), {"id": num}).first()
        if t_info and not task_service._is_potential_worker(
                db, ws, current_user.login, t_info[0], t_info[1], t_info[2]):
            raise NotAllowedException("NotAllowedException41")
    _verify_downloaded(db, ws, task_id, current_user.login)
    return {"status": "ok"}


@router.put(f"{PREFIX}/tasks/{{task_id}}/process")
@router.put(f"{PREFIX}/tasks/{{task_id}}/process/", include_in_schema=False)
def process_task(ws: str, task_id: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    wf_id, step, num = _parse_task_id(task_id)
    if wf_id is not None and step is not None:
        holder = task_service.process_task(
            db, ws, action=body.get("action", ""),
            comment=body.get("comment", ""),
            signature=body.get("signature", ""),
            user_login=current_user.login,
            workflow_id=wf_id, activity_step=step, task_num=num)
    else:
        holder = task_service.process_task(
            db, ws, task_id=int(num) if isinstance(num, int) else num,
            action=body.get("action", ""),
            comment=body.get("comment", ""),
            signature=body.get("signature", ""),
            user_login=current_user.login)
    return holder


@router.get(f"{PREFIX}/tasks/{{login}}/documents", response_model=List[DocumentRevisionDTO])
@router.get(f"{PREFIX}/tasks/{{login}}/documents/", include_in_schema=False)
def task_documents(ws: str, login: str,
                   filter: str = None,
                   db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    from app.models.document import DocumentRevision
    status_cond = "AND t.status < 2"
    if filter == "in_progress":
        status_cond = "AND t.status = 1"
    wf_rows = db.execute(text(
        f"SELECT DISTINCT t.workflow_id FROM task t "
        f"WHERE t.worker_login = :l AND t.worker_workspace_id = :w {status_cond}"
    ), {"l": login, "w": ws}).fetchall()
    wf_ids = [r[0] for r in wf_rows]
    if not wf_ids:
        return []
    docs = db.query(DocumentRevision).filter(
        DocumentRevision.workspace_id == ws,
        DocumentRevision.workflow_id.in_(wf_ids)
    ).all()
    # 对齐 Payara Tools.createLightDocumentRevisionDTO：清空 tags 与 workflow
    result = []
    for d in docs:
        dto = _doc_to_dict(db, d)
        dto["tags"] = []
        dto["workflow"] = None
        result.append(dto)
    return result


@router.get(f"{PREFIX}/tasks/{{login}}/parts", response_model=List[TaskHolderPartDTO])
@router.get(f"{PREFIX}/tasks/{{login}}/parts/", include_in_schema=False)
def task_parts(ws: str, login: str,
               filter: str = None,
               db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    from app.models.part import PartRevision
    status_cond = "AND t.status < 2"
    if filter == "in_progress":
        status_cond = "AND t.status = 1"
    wf_rows = db.execute(text(
        f"SELECT DISTINCT t.workflow_id FROM task t "
        f"WHERE t.worker_login = :l AND t.worker_workspace_id = :w {status_cond}"
    ), {"l": login, "w": ws}).fetchall()
    wf_ids = [r[0] for r in wf_rows]
    if not wf_ids:
        return []
    parts = db.query(PartRevision).filter(
        PartRevision.workspace_id == ws,
        PartRevision.workflow_id.in_(wf_ids)
    ).all()
    return [_part_to_dict(db, p) for p in parts]
