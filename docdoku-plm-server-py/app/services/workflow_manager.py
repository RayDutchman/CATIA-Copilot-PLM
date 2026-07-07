import uuid
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.models.workflow import WorkflowModel, Workflow, ActivityModel, TaskModel
from app.models.auth import Account
from app.models.security import ACL, AclUserEntry
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityConstraintException,
    EntityNotFoundException, NotAllowedException,
    WorkflowNotFoundException, WorkflowNameEmptyException,
)

logger = logging.getLogger(__name__)


class WorkflowService:
    # ========== ACL 辅助 ==========

    def _is_admin(self, db: Session, login: str) -> bool:
        return db.execute(text(
            "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
        ), {"l": login}).first() is not None

    def _has_read_access(self, db: Session, acl_id: int | None, user_login: str) -> bool:
        if acl_id is None:
            return True
        acl = db.query(ACL).filter(ACL.id == acl_id).first()
        if not acl or not acl.enabled:
            return True
        entry = db.query(AclUserEntry).filter(
            AclUserEntry.acl_id == acl_id,
            AclUserEntry.principal_login == user_login,
        ).first()
        if entry and entry.permission >= 1:  # READ_ONLY 或 FULL_ACCESS
            return True
        group_entry = db.execute(text(
            "SELECT 1 FROM aclusergroupentry ag "
            "JOIN usergroupmapping m ON ag.principal_id = m.groupname "
            "WHERE ag.acl_id = :acl AND m.login = :l AND ag.permission >= 1 LIMIT 1"
        ), {"acl": acl_id, "l": user_login}).first()
        return group_entry is not None

    def _check_write_access(self, db: Session, acl_id: int | None,
                            user_login: str) -> None:
        from app.services.factory.acl_factory import check_write_access
        if not check_write_access(db, acl_id, user_login, self._is_admin(db, user_login)):
            raise NotAllowedException("NotAllowedException34")

    def _is_potential_worker(self, db: Session, ws: str, user_login: str,
                               workflow_id: int, activity_step: int, task_num: int) -> bool:
        from app.services.task_manager import task_service
        return task_service._is_potential_worker(db, ws, user_login, workflow_id, activity_step, task_num)

    # ========== WorkflowModel CRUD ==========

    def list_models(self, db: Session, ws: str, user_login: str = None) -> list[WorkflowModel]:
        models = db.query(WorkflowModel).filter(
            WorkflowModel.workspace_id == ws).all()
        if not user_login:
            return models
        if self._is_admin(db, user_login):
            return models
        return [m for m in models
                if self._has_read_access(db, m.acl_id, user_login)]

    def get_model(self, db: Session, ws: str, model_id: str) -> WorkflowModel:
        m = db.query(WorkflowModel).filter(
            WorkflowModel.id == model_id, WorkflowModel.workspace_id == ws).first()
        if not m:
            raise EntityNotFoundException("WorkflowModelNotFoundException", model_id)
        return m

    def create_model(self, db: Session, ws: str, model_id: str,
                     final_state: str, user_login: str,
                     activity_models: list = None) -> WorkflowModel:
        if not model_id or not model_id.strip():
            raise WorkflowNameEmptyException("WorkflowNameEmptyException")
        if activity_models is not None:
            if not activity_models:
                raise NotAllowedException("NotAllowedException2")
            for am in activity_models:
                if not am.get("lifeCycleState"):
                    raise NotAllowedException("NotAllowedException3")
                tasks = am.get("tasks", [])
                if not tasks:
                    raise NotAllowedException("NotAllowedException3")
                for task in tasks:
                    if not task.get("role"):
                        raise NotAllowedException("NotAllowedException13")
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
                     activity_models: list = None,
                     user_login: str = None) -> WorkflowModel:
        m = self.get_model(db, ws, model_id)
        if user_login:
            self._check_write_access(db, m.acl_id, user_login)
        m.finalLifecycleState = final_state
        if activity_models is not None:
            # 删除旧 ActivityModel（级联删除旧 TaskModel）
            db.query(ActivityModel).filter(
                ActivityModel.workflowmodel_id == model_id,
                ActivityModel.workspace_id == ws,
            ).delete()
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

    def delete_model(self, db: Session, ws: str, model_id: str,
                     user_login: str = None):
        m = self.get_model(db, ws, model_id)
        if user_login:
            self._check_write_access(db, m.acl_id, user_login)
        # 检查是否被文档模板引用
        doc_tmpl = db.execute(text(
            "SELECT 1 FROM documentmastertemplate "
            "WHERE workflowmodel_id = :mid AND workspace_id = :ws LIMIT 1"
        ), {"mid": model_id, "ws": ws}).first()
        if doc_tmpl:
            raise EntityConstraintException("EntityConstraintException24")
        # 检查是否被零件模板引用
        part_tmpl = db.execute(text(
            "SELECT 1 FROM partmastertemplate "
            "WHERE workflowmodel_id = :mid AND workspace_id = :ws LIMIT 1"
        ), {"mid": model_id, "ws": ws}).first()
        if part_tmpl:
            raise EntityConstraintException("EntityConstraintException25")
        db.delete(m)
        db.commit()

    def get_instance(self, db: Session, ws: str, workflow_id: int) -> Workflow:
        w = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not w:
            raise WorkflowNotFoundException("WorkflowNotFoundException", str(workflow_id))
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
            raise WorkflowNotFoundException("WorkflowNotFoundException", str(workflow_id))
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
        # 检查每个 task 至少有一个 potential worker
        role_tasks = db.execute(text(
            "SELECT t.worker_login, t.worker_workspace_id, "
            "tm.role_name, tm.role_workspace_id "
            "FROM task t "
            "JOIN activity a ON t.workflow_id = a.workflow_id AND t.activity_step = a.step "
            "JOIN activitymodel am ON am.step = a.step AND am.workflowmodel_id = :mid "
            "    AND am.workspace_id = :ws "
            "JOIN taskmodel tm ON tm.activitymodel_id = am.id AND tm.num = t.num "
            "WHERE t.workflow_id = :wf_id AND tm.role_name IS NOT NULL AND t.worker_login IS NULL"
        ), {"wf_id": wf_id, "mid": model_id, "ws": ws}).fetchall()
        for rt in role_tasks:
            role_name, role_ws = rt[2], rt[3] or ws
            has_user = db.execute(text(
                "SELECT 1 FROM role_user WHERE role_name = :rn "
                "AND role_workspace_id = :rw LIMIT 1"
            ), {"rn": role_name, "rw": role_ws}).first()
            has_group = db.execute(text(
                "SELECT 1 FROM role_usergroup WHERE role_name = :rn "
                "AND role_workspace_id = :rw LIMIT 1"
            ), {"rn": role_name, "rw": role_ws}).first()
            if not has_user and not has_group:
                raise NotAllowedException("NotAllowedException56")
        # 将 step-0 的任务状态设为 IN_PROGRESS（1），启动工作流
        db.execute(text(
            "UPDATE task SET status = 1 WHERE workflow_id = :wf_id AND activity_step = 0"
        ), {"wf_id": wf_id})
        # 创建 workspace_workflow 记录
        ww_id = str(uuid.uuid4())
        db.execute(text(
            "INSERT INTO workspace_workflow (id, workspace_id, workflow_id) "
            "VALUES (:id, :ws, :wf_id)"
        ), {"id": ww_id, "ws": ws, "wf_id": wf_id})
        db.commit()
        logger.info("Workflow %s instantiated in workspace %s", wf_id, ws)
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
            raise WorkflowNotFoundException("WorkflowNotFoundException", str(wf_id))
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

    # ========== 通用 task 操作（委托给 TaskService）==========

    def _task_row_to_dict(self, row, db: Session = None) -> dict:
        from app.services.task_manager import task_service
        return task_service._task_row_to_dict(row, db)

    def get_task(self, db: Session, ws: str, workflow_id: int = None,
                 activity_step: int = None, task_num: int = None,
                 task_id: int = None):
        from app.services.task_manager import task_service
        return task_service.get_task(db, ws, workflow_id=workflow_id,
                                     activity_step=activity_step, task_num=task_num,
                                     task_id=task_id)

    def get_assigned_tasks(self, db: Session, ws: str, login: str) -> list:
        from app.services.task_manager import task_service
        return task_service.get_assigned_tasks(db, ws, login)

    def process_task(self, db: Session, ws: str, task_id: int = None,
                     action: str = "", comment: str = "", signature: str = "",
                     user_login: str = "", workflow_id: int = None,
                     activity_step: int = None, task_num: int = None,
                     skip_potential_worker_check: bool = False):
        from app.services.task_manager import task_service
        return task_service.process_task(
            db, ws, task_id=task_id, action=action, comment=comment,
            signature=signature, user_login=user_login,
            workflow_id=workflow_id, activity_step=activity_step,
            task_num=task_num,
            skip_potential_worker_check=skip_potential_worker_check)

    def approve_task_on_workspace_workflow(self, db: Session, ws: str,
                                            task_id: int, comment: str,
                                            signature: str, user_login: str) -> dict:
        from app.services.task_manager import task_service
        return task_service.approve_task_on_workspace_workflow(
            db, ws, task_id, comment, signature, user_login)

    def reject_task_on_workspace_workflow(self, db: Session, ws: str,
                                           task_id: int, comment: str,
                                           signature: str, user_login: str) -> dict:
        from app.services.task_manager import task_service
        return task_service.reject_task_on_workspace_workflow(
            db, ws, task_id, comment, signature, user_login)


workflow_service = WorkflowService()
