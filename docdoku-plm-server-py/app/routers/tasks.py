from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.workflow_manager import workflow_service, STATUS_MAP

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


def _doc_to_dict_short(rev):
    return {
        "id": f"{rev.documentmaster_id}-{rev.version}",
        "version": rev.version,
        "workspaceId": rev.workspace_id,
        "documentMasterId": rev.documentmaster_id,
        "title": rev.title or rev.documentmaster_id,
        "status": {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}.get(rev.status, "WIP"),
        "checkOutUser": None,
        "checkOutDate": None,
    }


@router.get(f"{PREFIX}/tasks/{{login}}/assigned")
@router.get(f"{PREFIX}/tasks/{{login}}/assigned/", include_in_schema=False)
def assigned_tasks(ws: str, login: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    return workflow_service.get_assigned_tasks(db, ws, login)


@router.get(f"{PREFIX}/tasks/{{task_id}}")
@router.get(f"{PREFIX}/tasks/{{task_id}}/", include_in_schema=False)
def get_task(ws: str, task_id: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    wf_id, step, num = _parse_task_id(task_id)
    if wf_id is not None and step is not None:
        t = workflow_service.get_task(db, ws, workflow_id=wf_id,
                                      activity_step=step, task_num=num)
    else:
        t = workflow_service.get_task(db, ws, task_id=int(num) if isinstance(num, int) else num)
    # t 是 row tuple，构建响应
    return {
        "num": t[0],
        "title": t[9] if len(t) > 9 else None,
        "instructions": t[4] if len(t) > 4 else None,
        "status": STATUS_MAP.get(t[7], "NOT_STARTED"),
        "worker": {"login": t[13]} if len(t) > 13 and t[13] else None,
        "closureComment": t[1] if len(t) > 1 else None,
        "signature": t[5] if len(t) > 5 else None,
        "closureDate": str(t[2]) if len(t) > 2 and t[2] else None,
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


@router.get(f"{PREFIX}/tasks/{{login}}/documents")
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
    return [_doc_to_dict_short(d) for d in docs]


@router.get(f"{PREFIX}/tasks/{{login}}/parts")
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
    return [{
        "partKey": f"{p.partmaster_partnumber}-{p.version}",
        "partNumber": p.partmaster_partnumber,
        "version": p.version,
        "name": p.name or p.partmaster_partnumber,
        "workspaceId": p.workspace_id,
    } for p in parts]
