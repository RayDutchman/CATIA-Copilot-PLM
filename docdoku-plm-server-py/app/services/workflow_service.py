from sqlalchemy.orm import Session
from datetime import datetime
from app.models.workflow import WorkflowModel, Activity, Task, Workflow, ActivityModel, TaskModel
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityNotFoundException,
    EntityConstraintException,
)

# task status 整数到字符串映射（Java / 前端期望字符串）
STATUS_MAP = {0: "NOT_STARTED", 1: "IN_PROGRESS", 2: "APPROVED", 3: "REJECTED"}


class WorkflowService:
    def list_models(self, db: Session, ws: str) -> list[WorkflowModel]:
        return db.query(WorkflowModel).filter(WorkflowModel.workspace_id == ws).all()

    def get_model(self, db: Session, ws: str, model_id: str) -> WorkflowModel:
        m = db.query(WorkflowModel).filter(
            WorkflowModel.id == model_id, WorkflowModel.workspace_id == ws).first()
        if not m:
            raise EntityNotFoundException("WorkflowModelNotFoundException", model_id)
        return m

    def create_model(self, db: Session, ws: str, model_id: str,
                     final_state: str, user_login: str,
                     activity_models: list = None) -> WorkflowModel:
        existing = db.query(WorkflowModel).filter(
            WorkflowModel.id == model_id, WorkflowModel.workspace_id == ws).first()
        if existing:
            raise EntityAlreadyExistsException("WorkflowModelAlreadyExistsException", model_id)
        m = WorkflowModel(id=model_id, workspace_id=ws,
                          finalLifecycleState=final_state,
                          creationdate=datetime.utcnow(),
                          author_login=user_login, author_workspace_id=ws)
        db.add(m)
        if activity_models:
            for am in activity_models:
                am_obj = ActivityModel(
                    step=am.get("step", 0),
                    dtype=am.get("type", ""),
                    lifecyclestate=am.get("lifeCycleState", ""),
                    workflowmodel_id=model_id,
                    workspace_id=ws,
                    taskstocomplete=am.get("tasksToComplete", 0),
                )
                db.add(am_obj)
                db.flush()
                for task in am.get("tasks", []):
                    db.add(TaskModel(
                        num=task.get("num", 0),
                        activitymodel_id=am_obj.id,
                        title=task.get("title", ""),
                        instructions=task.get("instructions", ""),
                        duration=task.get("duration"),
                        role_workspace_id=task.get("role", {}).get("workspaceId") if task.get("role") else None,
                        role_name=task.get("role", {}).get("name") if task.get("role") else None,
                    ))
        db.commit()
        db.refresh(m)
        return m

    def update_model(self, db: Session, ws: str, model_id: str,
                     final_state: str,
                     activity_models: list = None) -> WorkflowModel:
        m = self.get_model(db, ws, model_id)
        m.finalLifecycleState = final_state
        if activity_models is not None:
            db.query(ActivityModel).filter(
                ActivityModel.workflowmodel_id == model_id,
                ActivityModel.workspace_id == ws,
            ).delete()
            for am in activity_models:
                db.add(ActivityModel(
                    step=am.get("step", 0),
                    dtype=am.get("type", ""),
                    lifecyclestate=am.get("lifeCycleState", ""),
                    workflowmodel_id=model_id,
                    workspace_id=ws,
                    taskstocomplete=am.get("tasksToComplete", 0),
                ))
        db.commit()
        db.refresh(m)
        return m

    def delete_model(self, db: Session, ws: str, model_id: str):
        m = self.get_model(db, ws, model_id)
        db.delete(m)
        db.commit()

    def get_instance(self, db: Session, ws: str, workflow_id: int) -> Workflow:
        w = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not w:
            raise EntityNotFoundException("WorkflowNotFoundException", str(workflow_id))
        return w

    def list_workspace_workflows(self, db: Session, ws: str) -> list:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT w.* FROM workflow w "
            "JOIN activity a ON w.id = a.workflow_id "
            "JOIN task t ON a.workflow_id = w.id AND a.step = t.activity_step "
            "WHERE t.worker_workspace_id = :ws GROUP BY w.id"
        ), {"ws": ws}).fetchall()
        return rows

    def get_aborted_workflows_for_part(self, db: Session, ws: str,
                                        part_number: str, version: str) -> list:
        """查询零件关联的已中止工作流（aborteddate IS NOT NULL）。"""
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT w.id, w.aborteddate, w.finallifecyclestate "
            "FROM workflow w "
            "JOIN part_aborted_workflow paw ON w.id = paw.workflow_id "
            "WHERE paw.partmaster_workspace_id = :ws "
            "AND paw.partmaster_partnumber = :pn "
            "AND paw.partrevision_version = :v "
            "AND w.aborteddate IS NOT NULL"
        ), {"ws": ws, "pn": part_number, "v": version}).fetchall()
        return [{"id": r[0], "abortedDate": str(r[1]) if r[1] else None,
                 "finalLifecycleState": r[2]} for r in rows]

    def get_aborted_workflow_instance(self, db: Session, ws: str,
                                       workflow_id: int) -> dict:
        """获取已中止工作流实例的任务信息。"""
        from sqlalchemy import text
        row = db.execute(text(
            "SELECT id, aborteddate, finallifecyclestate "
            "FROM workflow WHERE id = :id AND aborteddate IS NOT NULL"
        ), {"id": workflow_id}).first()
        if not row:
            raise EntityNotFoundException("WorkflowNotFoundException", str(workflow_id))
        tasks = db.execute(text(
            "SELECT t.* FROM task t WHERE t.workflow_id = :id"
        ), {"id": workflow_id}).fetchall()
        return {
            "id": row[0],
            "abortedDate": str(row[1]) if row[1] else None,
            "finalLifecycleState": row[2],
            "tasks": [self._task_row_to_dict(t) for t in tasks],
        }

    def _task_row_to_dict(self, row) -> dict:
        return {
            "num": row[0],
            "title": row[4] if len(row) > 4 else None,
            "status": STATUS_MAP.get(row[7]) if len(row) > 7 else None,
            "worker": row[8] if len(row) > 8 else None,
            "closureComment": row[12] if len(row) > 12 else None,
            "closureDate": str(row[11]) if len(row) > 11 and row[11] else None,
            "signature": row[10] if len(row) > 10 else None,
        }

    def get_task(self, db: Session, ws: str, task_id: int):
        from sqlalchemy import text
        row = db.execute(text(
            "SELECT t.* FROM task t "
            "JOIN activity a ON t.workflow_id = a.workflow_id AND t.activity_step = a.step "
            "WHERE t.num = :id LIMIT 1"
        ), {"id": task_id}).first()
        if not row:
            raise EntityNotFoundException("TaskNotFoundException", str(task_id))
        return row

    def get_assigned_tasks(self, db: Session, ws: str, login: str) -> list:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT t.* FROM task t "
            "WHERE t.worker_login = :l AND t.worker_workspace_id = :w "
            "AND t.status < 2"
        ), {"l": login, "w": ws}).fetchall()
        result = []
        for t in rows:
            wf_id = t[2]  # workflow_id
            holder_type = None
            holder_reference = None
            holder_version = None
            # 检查文档
            doc = db.execute(text(
                "SELECT documentmaster_id, version FROM documentrevision "
                "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
            ), {"wf_id": wf_id, "ws": ws}).first()
            if doc:
                holder_type = "document"
                holder_reference = doc[0]
                holder_version = doc[1]
            else:
                # 检查零件
                part = db.execute(text(
                    "SELECT partmaster_partnumber, version FROM partrevision "
                    "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
                ), {"wf_id": wf_id, "ws": ws}).first()
                if part:
                    holder_type = "part"
                    holder_reference = part[0]
                    holder_version = part[1]
                else:
                    # 检查工作区工作流
                    ww = db.execute(text(
                        "SELECT id FROM workspace_workflow "
                        "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
                    ), {"wf_id": wf_id, "ws": ws}).first()
                    if ww:
                        holder_type = "workspace-workflow"
                        holder_reference = ww[0]
            result.append({
                "num": t[0],
                "title": t[4] if len(t) > 4 else None,
                "status": STATUS_MAP.get(t[7], "NOT_STARTED"),
                "holderType": holder_type,
                "holderReference": holder_reference,
                "holderVersion": holder_version,
                "workspaceId": ws,
            })
        return result

    def process_task(self, db: Session, ws: str, task_id: int,
                     action: str, comment: str, signature: str,
                     user_login: str):
        from sqlalchemy import text
        status = 2 if action.upper() == "APPROVE" else 3
        db.execute(text(
            "UPDATE task SET status = :s, closurecomment = :c, "
            "signature = :sig, closuredate = NOW() "
            "WHERE num = :id"
        ), {"s": status, "c": comment, "sig": signature, "id": task_id})

        # 获取 task 的关联信息，判断 holderType
        t_row = db.execute(text(
            "SELECT workflow_id FROM task WHERE num = :id LIMIT 1"
        ), {"id": task_id}).first()
        holder_type = None
        holder_reference = None
        holder_version = None
        if t_row:
            wf_id = t_row[0]
            # 检查是否挂载到文档
            doc = db.execute(text(
                "SELECT documentmaster_id, version FROM documentrevision "
                "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
            ), {"wf_id": wf_id, "ws": ws}).first()
            if doc:
                holder_type = "document"
                holder_reference = doc[0]
                holder_version = doc[1]
                # 更新文档状态（审批通过→RELEASED，拒绝→WIP）
                new_status = 1 if status == 2 else 0
                db.execute(text(
                    "UPDATE documentrevision SET status = :st "
                    "WHERE workspace_id = :ws AND documentmaster_id = :dm AND version = :v"
                ), {"st": new_status, "ws": ws, "dm": doc[0], "v": doc[1]})
            else:
                # 检查是否挂载到零件
                part = db.execute(text(
                    "SELECT partmaster_partnumber, version FROM partrevision "
                    "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
                ), {"wf_id": wf_id, "ws": ws}).first()
                if part:
                    holder_type = "part"
                    holder_reference = part[0]
                    holder_version = part[1]
                    # 更新零件状态
                    new_status = 1 if status == 2 else 0
                    db.execute(text(
                        "UPDATE partrevision SET status = :st "
                        "WHERE workspace_id = :ws AND partmaster_partnumber = :pn AND version = :v"
                    ), {"st": new_status, "ws": ws, "pn": part[0], "v": part[1]})
                else:
                    # 检查是否挂载到工作区工作流
                    ww = db.execute(text(
                        "SELECT id FROM workspace_workflow "
                        "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
                    ), {"wf_id": wf_id, "ws": ws}).first()
                    if ww:
                        holder_type = "workspace-workflow"
                        holder_reference = ww[0]
        db.commit()
        return {
            "holderType": holder_type,
            "holderReference": holder_reference,
            "holderVersion": holder_version,
            "workspaceId": ws,
        }


workflow_service = WorkflowService()
