from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException
from app.models.auth import Account
from app.models.workflow import Activity
from app.services.workflow_manager import workflow_service
from app.schemas.workflow import (
    WorkflowDTO, WorkflowAbortedDTO, WorkspaceWorkflowMinimalDTO,
)
from app.schemas.workspace_workflow import WorkspaceWorkflowDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _check_workspace_access(db: Session, ws: str, login: str):
    row = db.execute(text(
        "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :w"
    ), {"l": login, "w": ws}).first()
    if not row:
        raise AccessRightException("AccessRightException", login)


@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}", response_model=WorkflowDTO)
@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}/", include_in_schema=False)
def get_instance(ws: str, workflow_id: int, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    _check_workspace_access(db, ws, current_user.login)
    w = workflow_service.get_instance(db, ws, workflow_id)
    activities = db.query(Activity).filter(
        Activity.workflow_id == workflow_id).order_by(Activity.step).all()
    activity_dicts = []
    for a in activities:
        tasks = db.execute(text(
            "SELECT t.* FROM task t "
            "WHERE t.workflow_id = :wf_id AND t.activity_step = :step "
            "ORDER BY t.num"
        ), {"wf_id": workflow_id, "step": a.step}).fetchall()
        task_dicts = [workflow_service._task_row_to_dict(t, db) for t in tasks]
        activity_dicts.append({
            "step": a.step,
            "type": a.dtype,
            "lifeCycleState": a.lifecyclestate,
            "tasksToComplete": a.taskstocomplete,
            "tasks": task_dicts,
        })
    activity_dicts, current_step = workflow_service.enrich_activity_dicts(
        db, workflow_id, activity_dicts)
    return {
        "id": w.id,
        "abortedDate": w.aborteddate.isoformat() + "Z" if w.aborteddate else None,
        "finalLifecycleState": w.finallifecyclestate,
        "activities": activity_dicts,
        "currentStep": current_step,
    }


@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}/aborted", response_model=List[WorkflowAbortedDTO])
@router.get(f"{PREFIX}/workflow-instances/{{workflow_id}}/aborted/", include_in_schema=False)
def get_aborted(ws: str, workflow_id: int, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    _check_workspace_access(db, ws, current_user.login)
    return workflow_service.get_aborted_workflow_instance(db, ws, workflow_id)


@router.get(f"{PREFIX}/workspace-workflows", response_model=List[WorkspaceWorkflowMinimalDTO])
@router.get(f"{PREFIX}/workspace-workflows/", include_in_schema=False)
def list_wwf(ws: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    rows = workflow_service.list_workspace_workflows(db, ws)
    return [{"id": r[0], "abortedDate": r[1].isoformat() + "Z" if r[1] else None,
             "finalLifecycleState": r[2]} for r in rows]


# ========== workspace-workflow 实例化与管理 ==========

@router.get(f"{PREFIX}/workspace-workflows/{{id}}", response_model=WorkspaceWorkflowDTO)
@router.get(f"{PREFIX}/workspace-workflows/{{id}}/", include_in_schema=False)
def get_workspace_workflow(ws: str, id: str, db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user)):
    """获取 workspace_workflow 实例详情（含 activities/tasks 嵌套）"""
    _check_workspace_access(db, ws, current_user.login)
    result = workflow_service.get_workspace_workflow(db, ws, id)
    wf = result.get("workflow", {})
    if wf:
        wf_id = wf.get("id")
        activities = wf.get("activities", [])
        if wf_id is not None and activities:
            activities, current_step = workflow_service.enrich_activity_dicts(
                db, wf_id, activities)
            wf["activities"] = activities
            wf["currentStep"] = current_step
    return result


@router.post(f"{PREFIX}/workspace-workflows", status_code=201, response_model=WorkspaceWorkflowDTO)
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
