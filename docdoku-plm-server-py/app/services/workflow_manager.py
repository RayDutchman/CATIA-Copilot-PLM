import uuid
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text
from datetime import datetime
from app.models.workflow import WorkflowModel, Activity, Task, Workflow, ActivityModel, TaskModel
from app.models.auth import Account
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
            "tasks": [self._task_row_to_dict(t, db) for t in tasks],
        }

    # ========== workspace_workflow 实例化与管理 ==========

    def instantiate_workflow(self, db: Session, ws: str, model_id: str,
                              role_mapping: dict = None) -> dict:
        """从 workflow_model 实例化 workspace_workflow"""
        from sqlalchemy import text
        if role_mapping is None:
            role_mapping = {}
        wm = self.get_model(db, ws, model_id)
        ams = db.query(ActivityModel).filter(
            ActivityModel.workflowmodel_id == model_id,
            ActivityModel.workspace_id == ws,
        ).order_by(ActivityModel.step).all()
        if not ams:
            raise EntityNotFoundException("ActivityModelNotFoundException", model_id)
        # 创建 workflow 实例
        db.execute(text(
            "INSERT INTO workflow (aborteddate, finallifecyclestate) VALUES (NULL, :fls)"
        ), {"fls": wm.finalLifecycleState or ""})
        wf_row = db.execute(text("SELECT currval('workflow_id_seq')")).first()
        wf_id = wf_row[0]
        # 创建 activities 和 tasks
        for am in ams:
            db.execute(text(
                "INSERT INTO activity (step, dtype, lifecyclestate, workflow_id, taskstocomplete) "
                "VALUES (:step, :dtype, :lcs, :wf_id, :ttc)"
            ), {"step": am.step, "dtype": am.dtype or "",
                "lcs": am.lifecyclestate or "", "wf_id": wf_id,
                "ttc": am.taskstocomplete or 0})
            tms = db.query(TaskModel).filter(
                TaskModel.activitymodel_id == am.id,
            ).order_by(TaskModel.num).all()
            for tm in tms:
                worker_login = None
                worker_ws = None
                if tm.role_name and tm.role_workspace_id:
                    role_key = f"{tm.role_workspace_id}:{tm.role_name}"
                    if role_key in role_mapping:
                        worker_login = role_mapping[role_key]
                        worker_ws = tm.role_workspace_id
                db.execute(text(
                    "INSERT INTO task (num, activity_step, workflow_id, title, instructions, "
                    "status, worker_login, worker_workspace_id, duration) "
                    "VALUES (:num, :step, :wf_id, :title, :instructions, "
                    "0, :wl, :wws, :dur)"
                ), {"num": tm.num, "step": am.step, "wf_id": wf_id,
                    "title": tm.title or "", "instructions": tm.instructions or "",
                    "wl": worker_login, "wws": worker_ws,
                    "dur": tm.duration})
        # 创建 workspace_workflow 记录
        ww_id = str(uuid.uuid4())
        db.execute(text(
            "INSERT INTO workspace_workflow (id, workspace_id, workflow_id) "
            "VALUES (:id, :ws, :wf_id)"
        ), {"id": ww_id, "ws": ws, "wf_id": wf_id})
        db.commit()
        return {"id": ww_id, "workspaceId": ws, "workflowId": wf_id}

    def get_workspace_workflow(self, db: Session, ws: str, ww_id: str) -> dict:
        """查询 workspace_workflow 实例详情（含 activities/tasks 嵌套）"""
        from sqlalchemy import text
        ww = db.execute(text(
            "SELECT * FROM workspace_workflow WHERE id = :id AND workspace_id = :ws"
        ), {"id": ww_id, "ws": ws}).first()
        if not ww:
            raise EntityNotFoundException("WorkspaceWorkflowNotFoundException", ww_id)
        wf_id = ww[2]
        wf = db.execute(text(
            "SELECT * FROM workflow WHERE id = :id"
        ), {"id": wf_id}).first()
        if not wf:
            raise EntityNotFoundException("WorkflowNotFoundException", str(wf_id))
        activities = db.execute(text(
            "SELECT * FROM activity WHERE workflow_id = :id ORDER BY step"
        ), {"id": wf_id}).fetchall()
        activity_dicts = []
        for a in activities:
            tasks = db.execute(text(
                "SELECT t.* FROM task t "
                "WHERE t.workflow_id = :wf_id AND t.activity_step = :step "
                "ORDER BY t.num"
            ), {"wf_id": wf_id, "step": a[0]}).fetchall()
            task_dicts = [self._task_row_to_dict(t, db) for t in tasks]
            activity_dicts.append({
                "step": a[0],
                "type": a[1],
                "lifeCycleState": a[2],
                "tasksToComplete": a[4],
                "tasks": task_dicts,
            })
        return {
            "id": ww[0],
            "workspaceId": ws,
            "workflow": {
                "id": wf[0],
                "abortedDate": str(wf[1]) if wf[1] else None,
                "finalLifecycleState": wf[2],
                "activities": activity_dicts,
            },
        }

    def delete_workspace_workflow(self, db: Session, ws: str, ww_id: str):
        """删除 workspace_workflow 及其关联的 workflow"""
        from sqlalchemy import text
        ww = db.execute(text(
            "SELECT * FROM workspace_workflow WHERE id = :id AND workspace_id = :ws"
        ), {"id": ww_id, "ws": ws}).first()
        if not ww:
            raise EntityNotFoundException("WorkspaceWorkflowNotFoundException", ww_id)
        wf_id = ww[2]
        db.execute(text("DELETE FROM workspace_workflow WHERE id = :id"), {"id": ww_id})
        db.execute(text("DELETE FROM task WHERE workflow_id = :id"), {"id": wf_id})
        db.execute(text("DELETE FROM activity WHERE workflow_id = :id"), {"id": wf_id})
        db.execute(text("DELETE FROM workflow WHERE id = :id"), {"id": wf_id})
        db.commit()

    def get_aborted_workflows_for_workspace_workflow(self, db: Session, ws: str,
                                                      ww_id: str) -> dict:
        """查询 workspace_workflow 对应的 workflow 是否已中止"""
        from sqlalchemy import text
        ww = db.execute(text(
            "SELECT * FROM workspace_workflow WHERE id = :id AND workspace_id = :ws"
        ), {"id": ww_id, "ws": ws}).first()
        if not ww:
            raise EntityNotFoundException("WorkspaceWorkflowNotFoundException", ww_id)
        wf_id = ww[2]
        row = db.execute(text(
            "SELECT id, aborteddate, finallifecyclestate "
            "FROM workflow WHERE id = :id AND aborteddate IS NOT NULL"
        ), {"id": wf_id}).first()
        if not row:
            return {}
        tasks = db.execute(text(
            "SELECT t.* FROM task t WHERE t.workflow_id = :id"
        ), {"id": wf_id}).fetchall()
        return {
            "id": row[0],
            "abortedDate": str(row[1]) if row[1] else None,
            "finalLifecycleState": row[2],
            "tasks": [self._task_row_to_dict(t, db) for t in tasks],
        }

    # ========== 通用 task 操作 ==========

    def _task_row_to_dict(self, row, db: Session = None) -> dict:
        """将 SELECT t.* 的行转为字典（列序: num,closurecomment,closuredate,duration,
           instructions,signature,startdate,status,targetiteration,title,
           activity_step,workflow_id,worker_workspace_id,worker_login）"""
        worker_login = row[13] if len(row) > 13 else None
        worker = None
        if worker_login and db:
            acc = db.query(Account).filter(Account.login == worker_login).first()
            if acc:
                worker = {"login": acc.login, "name": acc.name,
                          "email": acc.email,
                          "workspaceId": row[12] if len(row) > 12 else None}
            else:
                worker = {"login": worker_login, "name": worker_login}
        return {
            "num": row[0],
            "title": row[9] if len(row) > 9 else None,
            "instructions": row[4] if len(row) > 4 else None,
            "status": STATUS_MAP.get(row[7]) if len(row) > 7 else None,
            "worker": worker,
            "closureComment": row[1] if len(row) > 1 else None,
            "closureDate": str(row[2]) if len(row) > 2 and row[2] else None,
            "closingDate": str(row[2]) if len(row) > 2 and row[2] else None,
            "signature": row[5] if len(row) > 5 else None,
        }

    def get_task(self, db: Session, ws: str, workflow_id: int = None,
                 activity_step: int = None, task_num: int = None,
                 task_id: int = None):
        """支持复合键(workflow_id, step, num)或旧版单 num 查询"""
        from sqlalchemy import text
        if workflow_id is not None and activity_step is not None and task_num is not None:
            row = db.execute(text(
                "SELECT t.* FROM task t "
                "WHERE t.workflow_id = :wf_id AND t.activity_step = :step AND t.num = :num LIMIT 1"
            ), {"wf_id": workflow_id, "step": activity_step, "num": task_num}).first()
        else:
            row = db.execute(text(
                "SELECT t.* FROM task t "
                "JOIN activity a ON t.workflow_id = a.workflow_id AND t.activity_step = a.step "
                "WHERE t.num = :id LIMIT 1"
            ), {"id": task_id}).first()
        if not row:
            raise EntityNotFoundException("TaskNotFoundException", str(task_id or task_num))
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
            wf_id = t[11] if len(t) > 11 else None  # workflow_id
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
            # 构建 worker 信息
            worker_login = t[13] if len(t) > 13 else None
            worker_ws = t[12] if len(t) > 12 else None
            worker = None
            if worker_login:
                acc = db.query(Account).filter(Account.login == worker_login).first()
                if acc:
                    worker = {"login": acc.login, "name": acc.name or acc.login,
                              "email": acc.email, "workspaceId": worker_ws}
                else:
                    worker = {"login": worker_login, "name": worker_login,
                              "workspaceId": worker_ws}
            result.append({
                "num": t[0],
                "workflowId": wf_id,
                "activityStep": t[10] if len(t) > 10 else None,
                "title": t[9] if len(t) > 9 else None,
                "instructions": t[4] if len(t) > 4 else None,
                "status": STATUS_MAP.get(t[7], "NOT_STARTED"),
                "worker": worker,
                "closureComment": t[1] if len(t) > 1 else None,
                "signature": t[5] if len(t) > 5 else None,
                "closureDate": str(t[2]) if len(t) > 2 and t[2] else None,
                "holderType": holder_type,
                "holderReference": holder_reference,
                "holderVersion": holder_version,
                "workspaceId": ws,
            })
        return result

    def process_task(self, db: Session, ws: str, task_id: int = None,
                     action: str = "", comment: str = "", signature: str = "",
                     user_login: str = "", workflow_id: int = None,
                     activity_step: int = None, task_num: int = None):
        from sqlalchemy import text
        status = 2 if action.upper() == "APPROVE" else 3
        if workflow_id is not None and activity_step is not None and task_num is not None:
            db.execute(text(
                "UPDATE task SET status = :s, closurecomment = :c, "
                "signature = :sig, closuredate = NOW() "
                "WHERE workflow_id = :wf_id AND activity_step = :step AND num = :num"
            ), {"s": status, "c": comment, "sig": signature,
                "wf_id": workflow_id, "step": activity_step, "num": task_num})
            t_row = db.execute(text(
                "SELECT workflow_id FROM task "
                "WHERE workflow_id = :wf_id AND activity_step = :step AND num = :num LIMIT 1"
            ), {"wf_id": workflow_id, "step": activity_step, "num": task_num}).first()
        else:
            db.execute(text(
                "UPDATE task SET status = :s, closurecomment = :c, "
                "signature = :sig, closuredate = NOW() "
                "WHERE num = :id"
            ), {"s": status, "c": comment, "sig": signature, "id": task_id})
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
                    new_status = 1 if status == 2 else 0
                    db.execute(text(
                        "UPDATE partrevision SET status = :st "
                        "WHERE workspace_id = :ws AND partmaster_partnumber = :pn AND version = :v"
                    ), {"st": new_status, "ws": ws, "pn": part[0], "v": part[1]})
                else:
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

    def approve_task_on_workspace_workflow(self, db: Session, ws: str,
                                            task_id: int, comment: str,
                                            signature: str, user_login: str) -> dict:
        return self.process_task(db, ws, task_id=task_id, action="APPROVE",
                                 comment=comment, signature=signature,
                                 user_login=user_login)

    def reject_task_on_workspace_workflow(self, db: Session, ws: str,
                                           task_id: int, comment: str,
                                           signature: str, user_login: str) -> dict:
        return self.process_task(db, ws, task_id=task_id, action="REJECT",
                                 comment=comment, signature=signature,
                                 user_login=user_login)


workflow_service = WorkflowService()
