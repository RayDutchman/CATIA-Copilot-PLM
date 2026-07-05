from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.workflow_service import workflow_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _model_to_dict(m) -> dict:
    return {
        "id": m.id,
        "workspaceId": m.workspace_id,
        "finalLifecycleState": m.finalLifecycleState or "",
        "creationDate": m.creationdate.isoformat() + "Z" if m.creationdate else None,
        "author": {"login": m.author_login or "", "name": m.author_login or ""},
        "activityModels": [],
        "acl": None,
    }


@router.get(f"{PREFIX}/workflow-models")
def list_models(ws: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    return [_model_to_dict(m) for m in workflow_service.list_models(db, ws)]


@router.get(f"{PREFIX}/workflow-models/{{model_id}}")
def get_model(ws: str, model_id: str, db: Session = Depends(get_db),
              current_user: Account = Depends(get_current_user)):
    return _model_to_dict(workflow_service.get_model(db, ws, model_id))


@router.post(f"{PREFIX}/workflow-models", status_code=201)
@router.post(f"{PREFIX}/workflow-models/", status_code=201, include_in_schema=False)
def create_model(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    m = workflow_service.create_model(db, ws, body.get("id", ""),
                                      body.get("finalLifecycleState", ""),
                                      current_user.login)
    return _model_to_dict(m)


@router.put(f"{PREFIX}/workflow-models/{{model_id}}")
@router.put(f"{PREFIX}/workflow-models/{{model_id}}/", include_in_schema=False)
def update_model(ws: str, model_id: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    m = workflow_service.update_model(db, ws, model_id,
                                      body.get("finalLifecycleState", ""))
    return _model_to_dict(m)


@router.delete(f"{PREFIX}/workflow-models/{{model_id}}", status_code=204)
@router.delete(f"{PREFIX}/workflow-models/{{model_id}}/", status_code=204, include_in_schema=False)
def delete_model(ws: str, model_id: str, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    workflow_service.delete_model(db, ws, model_id)


@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}")
def get_instance(ws: str, workflow_id: int, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    w = workflow_service.get_instance(db, ws, workflow_id)
    return {"id": w.id, "abortedDate": w.aborteddate, "finalLifecycleState": w.finallifecyclestate,
            "activities": [], "currentStep": 0}


@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}/aborted")
def get_aborted(ws: str, workflow_id: int, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    return []


@router.get(f"{PREFIX}/workspace-workflows")
def list_wwf(ws: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    return []


@router.get(f"{PREFIX}/tasks/{{login}}/assigned")
def assigned_tasks(ws: str, login: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    tasks = workflow_service.get_assigned_tasks(db, ws, login)
    return [{"num": t[0], "title": t[4], "status": t[7]} for t in tasks]


@router.get(f"{PREFIX}/tasks/{{task_id}}")
def get_task(ws: str, task_id: int, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    t = workflow_service.get_task(db, ws, task_id)
    return {"num": t[0], "title": t[4], "status": t[7]}


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
