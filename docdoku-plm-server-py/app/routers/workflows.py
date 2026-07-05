from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException
from app.models.auth import Account
from app.models.workflow import Activity
from app.models.security import ACL, AclUserEntry, AclUserGroupEntry
from app.services.workflow_service import workflow_service, STATUS_MAP

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _check_workspace_access(db: Session, ws: str, login: str):
    """检查用户是否有工作区访问权限，无权限时抛出 AccessRightException(403)。"""
    row = db.execute(text(
        "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :w"
    ), {"l": login, "w": ws}).first()
    if not row:
        raise AccessRightException("AccessRightException")


def _model_to_dict(m, db: Session = None) -> dict:
    author_login = m.author_login or ""
    author_name = author_login
    author_email = ""
    author_language = "en"
    if db and author_login:
        acc = db.query(Account).filter(Account.login == author_login).first()
        if acc:
            author_name = acc.name or author_login
            author_email = acc.email or ""
            author_language = acc.language or "en"

    acl_data = None
    if db and m.acl_id:
        acl = db.query(ACL).filter(ACL.id == m.acl_id).first()
        if acl:
            user_entries = db.query(AclUserEntry).filter(
                AclUserEntry.acl_id == m.acl_id).all()
            group_entries = db.query(AclUserGroupEntry).filter(
                AclUserGroupEntry.acl_id == m.acl_id).all()
            acl_data = {
                "userEntries": {
                    f"{e.principal_login}:{e.principal_workspace_id}": e.permission
                    for e in user_entries
                },
                "groupEntries": {
                    f"{e.principal_id}:{e.principal_workspace_id}": e.permission
                    for e in group_entries
                },
            }

    result = {
        "id": m.id,
        "finalLifeCycleState": m.finalLifecycleState or "",
        "creationDate": m.creationdate.isoformat() + "Z" if m.creationdate else None,
        "author": {
            "login": author_login,
            "name": author_name,
            "email": author_email,
            "language": author_language,
            "workspaceId": m.workspace_id,
        },
        "activityModels": [],
    }
    if acl_data is not None:
        result["acl"] = acl_data
    return result


@router.get(f"{PREFIX}/workflow-models")
def list_models(ws: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    return [_model_to_dict(m, db) for m in workflow_service.list_models(db, ws)]


@router.get(f"{PREFIX}/workflow-models/{{model_id}}")
def get_model(ws: str, model_id: str, db: Session = Depends(get_db),
              current_user: Account = Depends(get_current_user)):
    return _model_to_dict(workflow_service.get_model(db, ws, model_id), db)


@router.post(f"{PREFIX}/workflow-models", status_code=201)
@router.post(f"{PREFIX}/workflow-models/", status_code=201, include_in_schema=False)
def create_model(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    m = workflow_service.create_model(db, ws, body.get("id", ""),
                                       body.get("finalLifecycleState", ""),
                                       current_user.login)
    return _model_to_dict(m, db)


@router.put(f"{PREFIX}/workflow-models/{{model_id}}")
@router.put(f"{PREFIX}/workflow-models/{{model_id}}/", include_in_schema=False)
def update_model(ws: str, model_id: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    activity_models = body.get("activityModels")
    m = workflow_service.update_model(db, ws, model_id,
                                       body.get("finalLifecycleState", ""),
                                       activity_models=activity_models)
    result = _model_to_dict(m, db)
    if activity_models:
        result["activityModels"] = activity_models
    return result


@router.delete(f"{PREFIX}/workflow-models/{{model_id}}", status_code=204)
@router.delete(f"{PREFIX}/workflow-models/{{model_id}}/", status_code=204, include_in_schema=False)
def delete_model(ws: str, model_id: str, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    workflow_service.delete_model(db, ws, model_id)


@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}")
def get_instance(ws: str, workflow_id: int, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    _check_workspace_access(db, ws, current_user.login)
    w = workflow_service.get_instance(db, ws, workflow_id)
    activities = db.query(Activity).filter(
        Activity.workflow_id == workflow_id).all()
    activity_dicts = [{
        "step": a.step,
        "type": a.dtype,
        "lifeCycleState": a.lifecyclestate,
        "tasksToComplete": a.taskstocomplete,
    } for a in activities]
    return {
        "id": w.id,
        "abortedDate": str(w.aborteddate) if w.aborteddate else None,
        "finalLifecycleState": w.finallifecyclestate,
        "activities": activity_dicts,
        "currentStep": 0,
    }


@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}/aborted")
def get_aborted(ws: str, workflow_id: int, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    _check_workspace_access(db, ws, current_user.login)
    return workflow_service.get_aborted_workflow_instance(db, ws, workflow_id)


@router.get(f"{PREFIX}/workspace-workflows")
def list_wwf(ws: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    rows = workflow_service.list_workspace_workflows(db, ws)
    return [{"id": r[0], "abortedDate": str(r[1]) if r[1] else None,
             "finalLifecycleState": r[2]} for r in rows]


@router.get(f"{PREFIX}/tasks/{{login}}/assigned")
def assigned_tasks(ws: str, login: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    tasks = workflow_service.get_assigned_tasks(db, ws, login)
    return [{"num": t[0], "title": t[4],
             "status": STATUS_MAP.get(t[7], "NOT_STARTED")} for t in tasks]


@router.get(f"{PREFIX}/tasks/{{task_id}}")
def get_task(ws: str, task_id: int, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    t = workflow_service.get_task(db, ws, task_id)
    return {"num": t[0], "title": t[4],
            "status": STATUS_MAP.get(t[7], "NOT_STARTED")}


@router.put(f"{PREFIX}/tasks/{{task_id}}/process")
@router.put(f"{PREFIX}/tasks/{{task_id}}/process/", include_in_schema=False)
def process_task(ws: str, task_id: int, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    workflow_service.process_task(db, ws, task_id,
                                  body.get("action", ""),
                                  body.get("comment", ""),
                                  body.get("signature", ""),
                                  current_user.login)
    return {"status": "ok"}


@router.get(f"{PREFIX}/tasks/{{login}}/documents")
def task_documents(ws: str, login: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    return []


@router.get(f"{PREFIX}/tasks/{{login}}/parts")
def task_parts(ws: str, login: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return []
