from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.security import ACL, AclUserEntry, AclUserGroupEntry
from app.services.workflow_manager import workflow_service
from app.services.acl_helper import apply_acl
from app.schemas.workflow import WorkflowModelDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


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
            _PERM = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}
            acl_data = {
                "userEntries": [{"key": e.principal_login, "value": _PERM.get(e.permission, "FORBIDDEN")} for e in user_entries],
                "groupEntries": [{"key": e.principal_id, "value": _PERM.get(e.permission, "FORBIDDEN")} for e in group_entries],
                "userEntriesMap": {e.principal_login: _PERM.get(e.permission, "FORBIDDEN") for e in user_entries},
                "userGroupEntriesMap": {},
            }

    activity_models = []
    if db:
        from app.models.workflow import ActivityModel, TaskModel
        ams = db.query(ActivityModel).filter(
            ActivityModel.workflowmodel_id == m.id,
            ActivityModel.workspace_id == m.workspace_id,
        ).order_by(ActivityModel.step).all()
        activity_models = [{
            "step": a.step,
            "type": a.dtype,
            "lifeCycleState": a.lifecyclestate,
            "tasksToComplete": a.taskstocomplete,
            "tasks": [{
                "num": t.num,
                "title": t.title or "",
                "instructions": t.instructions or "",
                "duration": t.duration,
                "role": {
                    "name": t.role_name or "",
                    "workspaceId": t.role_workspace_id or m.workspace_id,
                },
            } for t in db.query(TaskModel).filter(
                TaskModel.activitymodel_id == a.id,
            ).order_by(TaskModel.num).all()],
        } for a in ams]

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
        "activityModels": activity_models,
    }
    if acl_data is not None:
        result["acl"] = acl_data
    return result


@router.get(f"{PREFIX}/workflow-models", response_model=List[WorkflowModelDTO])
@router.get(f"{PREFIX}/workflow-models/", include_in_schema=False)
def list_models(ws: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    return [_model_to_dict(m, db) for m in
            workflow_service.list_models(db, ws, current_user.login)]


@router.get(f"{PREFIX}/workflow-models/{{model_id}}", response_model=WorkflowModelDTO)
@router.get(f"{PREFIX}/workflow-models/{{model_id}}/", include_in_schema=False)
def get_model(ws: str, model_id: str, db: Session = Depends(get_db),
              current_user: Account = Depends(get_current_user)):
    return _model_to_dict(workflow_service.get_model(db, ws, model_id), db)


@router.post(f"{PREFIX}/workflow-models", status_code=201, response_model=WorkflowModelDTO)
@router.post(f"{PREFIX}/workflow-models/", status_code=201, include_in_schema=False)
def create_model(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    m = workflow_service.create_model(db, ws, body.get("id", ""),
                                       body.get("finalLifecycleState", ""),
                                       current_user.login,
                                       activity_models=body.get("activityModels"))
    return _model_to_dict(m, db)


@router.put(f"{PREFIX}/workflow-models/{{model_id}}", response_model=WorkflowModelDTO)
@router.put(f"{PREFIX}/workflow-models/{{model_id}}/", include_in_schema=False)
def update_model(ws: str, model_id: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    activity_models = body.get("activityModels")
    m = workflow_service.update_model(db, ws, model_id,
                                       body.get("finalLifecycleState", ""),
                                       activity_models=activity_models,
                                       user_login=current_user.login)
    return _model_to_dict(m, db)


@router.delete(f"{PREFIX}/workflow-models/{{model_id}}", status_code=204)
@router.delete(f"{PREFIX}/workflow-models/{{model_id}}/", status_code=204, include_in_schema=False)
def delete_model(ws: str, model_id: str, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    workflow_service.delete_model(db, ws, model_id, user_login=current_user.login)


@router.put(f"{PREFIX}/workflow-models/{{model_id}}/acl", response_model=WorkflowModelDTO)
@router.put(f"{PREFIX}/workflow-models/{{model_id}}/acl/", include_in_schema=False)
def update_model_acl(ws: str, model_id: str, body: dict, db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    m = workflow_service.get_model(db, ws, model_id)
    new_acl_id = apply_acl(db, m.acl_id,
                           body.get("userEntries", {}),
                           body.get("groupEntries", {}))
    m.acl_id = new_acl_id
    db.commit()
    return _model_to_dict(m, db)
