from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.workflow_manager import workflow_service, STATUS_MAP
from app.schemas.workflow import (
    TaskWrapperDTO, TaskHolderDocDTO, TaskHolderPartDTO,
)

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


def _doc_to_dict(rev):
    return {
        "id": f"{rev.documentmaster_id}-{rev.version}",
        "version": rev.version,
        "workspaceId": rev.workspace_id,
        "documentMasterId": rev.documentmaster_id,
        "title": rev.title or rev.documentmaster_id,
        "description": rev.description or "",
        "type": rev.document_master.type if rev.document_master else "",
        "status": {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}.get(rev.status, "WIP"),
        "checkOutUser": {"login": rev.checkout_user_login} if rev.checkout_user_login else None,
        "checkOutDate": int(rev.check_out_date.timestamp() * 1000) if rev.check_out_date else None,
        "path": rev.location_completepath or "",
        "author": {"login": rev.author_login, "name": rev.author_login},
        "creationDate": int(rev.creation_date.timestamp() * 1000) if rev.creation_date else None,
    }


def _part_to_dict(rev):
    return {
        "partKey": f"{rev.partmaster_partnumber}-{rev.version}",
        "partNumber": rev.partmaster_partnumber,
        "version": rev.version,
        "name": rev.name or rev.partmaster_partnumber,
        "workspaceId": rev.workspace_id,
        "description": rev.description or "",
        "type": rev.part_master.type if rev.part_master else "",
        "status": {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}.get(rev.status, "WIP"),
        "checkOutUser": {"login": rev.checkout_user_login} if rev.checkout_user_login else None,
        "checkOutDate": int(rev.check_out_date.timestamp() * 1000) if rev.check_out_date else None,
        "standardPart": rev.part_master.standard_part if rev.part_master else False,
        "author": {"login": rev.author_login, "name": rev.author_login},
        "creationDate": int(rev.creation_date.timestamp() * 1000) if rev.creation_date else None,
    }


@router.get(f"{PREFIX}/tasks/{{login}}/assigned", response_model=List[TaskWrapperDTO])
@router.get(f"{PREFIX}/tasks/{{login}}/assigned/", include_in_schema=False)
def assigned_tasks(ws: str, login: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    return workflow_service.get_assigned_tasks(db, ws, login)


@router.get(f"{PREFIX}/tasks/{{task_id}}", response_model=TaskWrapperDTO)
@router.get(f"{PREFIX}/tasks/{{task_id}}/", include_in_schema=False)
def get_task(ws: str, task_id: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    wf_id, step, num = _parse_task_id(task_id)
    if wf_id is not None and step is not None:
        t = workflow_service.get_task(db, ws, workflow_id=wf_id,
                                       activity_step=step, task_num=num)
    else:
        t = workflow_service.get_task(db, ws, task_id=int(num) if isinstance(num, int) else num)
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
            holder_type = "document"
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
    return {
        "num": t[0],
        "title": t[9] if len(t) > 9 else None,
        "instructions": t[4] if len(t) > 4 else None,
        "status": STATUS_MAP.get(t[7], "NOT_STARTED"),
        "worker": {"login": t[13]} if len(t) > 13 and t[13] else None,
        "closureComment": t[1] if len(t) > 1 else None,
        "signature": t[5] if len(t) > 5 else None,
        "closureDate": t[2].isoformat() + "Z" if len(t) > 2 and t[2] else None,
        "holderType": holder_type,
        "holderReference": holder_reference,
        "holderVersion": holder_version,
        "workspaceId": ws,
    }


@router.put(f"{PREFIX}/tasks/{{task_id}}/process")
@router.put(f"{PREFIX}/tasks/{{task_id}}/process/", include_in_schema=False)
def process_task(ws: str, task_id: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    wf_id, step, num = _parse_task_id(task_id)
    if wf_id is not None and step is not None:
        holder = workflow_service.process_task(
            db, ws, action=body.get("action", ""),
            comment=body.get("comment", ""),
            signature=body.get("signature", ""),
            user_login=current_user.login,
            workflow_id=wf_id, activity_step=step, task_num=num)
    else:
        holder = workflow_service.process_task(
            db, ws, task_id=int(num) if isinstance(num, int) else num,
            action=body.get("action", ""),
            comment=body.get("comment", ""),
            signature=body.get("signature", ""),
            user_login=current_user.login)
    return holder


@router.get(f"{PREFIX}/tasks/{{login}}/documents", response_model=List[TaskHolderDocDTO])
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
    return [_doc_to_dict(d) for d in docs]


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
    return [_part_to_dict(p) for p in parts]
