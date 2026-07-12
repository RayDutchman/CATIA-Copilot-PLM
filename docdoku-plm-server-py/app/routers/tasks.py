from typing import List
from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotAllowedException
from app.models.auth import Account
from app.services.task_manager import task_service
from app.schemas.workflow import (
    TaskWrapperDTO, TaskHolderPartDTO,
)
from app.schemas.document.document_revision import DocumentRevisionDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


@router.get(f"{PREFIX}/tasks/{{login}}/assigned", response_model=List[TaskWrapperDTO])
@router.get(f"{PREFIX}/tasks/{{login}}/assigned/", include_in_schema=False)
def assigned_tasks(ws: str, login: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    return task_service.get_assigned_tasks(db, ws, login)


@router.get(f"{PREFIX}/tasks/{{task_id}}", response_model=TaskWrapperDTO)
@router.get(f"{PREFIX}/tasks/{{task_id}}/", include_in_schema=False)
def get_task(ws: str, task_id: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    return task_service.get_task_dto(db, ws, task_id)


@router.put(f"{PREFIX}/tasks/{{task_id}}/check")
@router.put(f"{PREFIX}/tasks/{{task_id}}/check/", include_in_schema=False)
def check_task(ws: str, task_id: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    wf_id, step, num = task_service._parse_task_id(task_id)
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
    task_service.verify_downloaded(db, ws, task_id, current_user.login)
    return {"status": "ok"}


@router.put(f"{PREFIX}/tasks/{{task_id}}/process")
@router.put(f"{PREFIX}/tasks/{{task_id}}/process/", include_in_schema=False)
def process_task(ws: str, task_id: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    wf_id, step, num = task_service._parse_task_id(task_id)
    if wf_id is not None and step is not None:
        task_service.process_task(
            db, ws, action=body.get("action", ""),
            comment=body.get("comment", ""),
            signature=body.get("signature", ""),
            user_login=current_user.login,
            workflow_id=wf_id, activity_step=step, task_num=num)
    else:
        task_service.process_task(
            db, ws, task_id=int(num) if isinstance(num, int) else num,
            action=body.get("action", ""),
            comment=body.get("comment", ""),
            signature=body.get("signature", ""),
            user_login=current_user.login)
    return Response(status_code=204)


@router.get(f"{PREFIX}/tasks/{{login}}/documents", response_model=List[DocumentRevisionDTO])
@router.get(f"{PREFIX}/tasks/{{login}}/documents/", include_in_schema=False)
def task_documents(ws: str, login: str,
                   filter: str = None,
                   db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    return task_service.get_task_documents(db, ws, login, filter)


@router.get(f"{PREFIX}/tasks/{{login}}/parts", response_model=List[TaskHolderPartDTO])
@router.get(f"{PREFIX}/tasks/{{login}}/parts/", include_in_schema=False)
def task_parts(ws: str, login: str,
               filter: str = None,
               db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return task_service.get_task_parts(db, ws, login, filter)
