from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException
from app.models.auth import Account
from app.models.workflow import Activity
from app.services.workflow_manager import workflow_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _check_workspace_access(db: Session, ws: str, login: str):
    row = db.execute(text(
        "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :w"
    ), {"l": login, "w": ws}).first()
    if not row:
        raise AccessRightException("AccessRightException")


@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}")
@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}/", include_in_schema=False)
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
@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}/aborted/", include_in_schema=False)
def get_aborted(ws: str, workflow_id: int, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    _check_workspace_access(db, ws, current_user.login)
    return workflow_service.get_aborted_workflow_instance(db, ws, workflow_id)


@router.get(f"{PREFIX}/workspace-workflows")
@router.get(f"{PREFIX}/workspace-workflows/", include_in_schema=False)
def list_wwf(ws: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    rows = workflow_service.list_workspace_workflows(db, ws)
    return [{"id": r[0], "abortedDate": str(r[1]) if r[1] else None,
             "finalLifecycleState": r[2]} for r in rows]


# ========== workspace-workflow 实例化与管理 ==========

@router.get(f"{PREFIX}/workspace-workflows/{{id}}")
@router.get(f"{PREFIX}/workspace-workflows/{{id}}/", include_in_schema=False)
def get_workspace_workflow(ws: str, id: str, db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user)):
    """获取 workspace_workflow 实例详情（含 activities/tasks 嵌套）"""
    _check_workspace_access(db, ws, current_user.login)
    return workflow_service.get_workspace_workflow(db, ws, id)


@router.post(f"{PREFIX}/workspace-workflows", status_code=201)
@router.post(f"{PREFIX}/workspace-workflows/", status_code=201, include_in_schema=False)
def create_workspace_workflow(ws: str, body: dict, db: Session = Depends(get_db),
                              current_user: Account = Depends(get_current_user)):
    """从 workflow model 实例化 workspace_workflow"""
    _check_workspace_access(db, ws, current_user.login)
    return workflow_service.instantiate_workflow(
        db, ws, body.get("workflowModelId", ""),
        role_mapping=body.get("roleMapping", {}))


@router.delete(f"{PREFIX}/workspace-workflows/{{id}}", status_code=204)
@router.delete(f"{PREFIX}/workspace-workflows/{{id}}/", status_code=204, include_in_schema=False)
def delete_workspace_workflow(ws: str, id: str, db: Session = Depends(get_db),
                              current_user: Account = Depends(get_current_user)):
    """删除 workspace_workflow 及其关联的 workflow"""
    _check_workspace_access(db, ws, current_user.login)
    workflow_service.delete_workspace_workflow(db, ws, id)


@router.get(f"{PREFIX}/workspace-workflows/{{workflowId}}/aborted")
@router.get(f"{PREFIX}/workspace-workflows/{{workflowId}}/aborted/", include_in_schema=False)
def workflow_aborted(ws: str, workflowId: str, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    """查询 workspace_workflow 对应的 workflow 是否已中止"""
    _check_workspace_access(db, ws, current_user.login)
    return workflow_service.get_aborted_workflows_for_workspace_workflow(db, ws, workflowId)
