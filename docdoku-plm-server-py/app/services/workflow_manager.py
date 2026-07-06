import uuid
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.models.workflow import WorkflowModel, Workflow, ActivityModel, TaskModel
from app.models.auth import Account
from app.models.security import ACL, AclUserEntry
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityConstraintException,
    EntityNotFoundException, NotAllowedException,
)

# task status 整数到字符串映射（Java / 前端期望字符串）
STATUS_MAP = {0: "NOT_STARTED", 1: "IN_PROGRESS", 2: "APPROVED", 3: "REJECTED"}


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
        from app.services.acl_helper import check_write_access
        if not check_write_access(db, acl_id, user_login, self._is_admin(db, user_login)):
            raise NotAllowedException("NotAllowedException34")

    def _is_potential_worker(self, db: Session, ws: str, user_login: str,
                              workflow_id: int, activity_step: int, task_num: int) -> bool:
        """检查用户是否是该 task 的 potential worker（通过角色分配）。"""
        task_role = db.execute(text(
            "SELECT tm.role_name, tm.role_workspace_id FROM taskmodel tm "
            "JOIN activitymodel am ON tm.activitymodel_id = am.id "
            "JOIN activity a ON am.step = a.step AND a.workflow_id = :wf_id "
            "WHERE a.workflow_id = :wf_id AND a.step = :step AND tm.num = :num "
            "LIMIT 1"
        ), {"wf_id": workflow_id, "step": activity_step, "num": task_num}).first()
        if not task_role or not task_role[0]:
            return True  # 无角色限制 = 任何人是 potential worker
        role_name = task_role[0]
        role_ws = task_role[1] or ws
        # 检查用户是否在该角色中
        in_role = db.execute(text(
            "SELECT 1 FROM role_user WHERE role_name = :rn AND role_workspace_id = :rw "
            "AND user_login = :l AND user_workspace_id = :ws LIMIT 1"
        ), {"rn": role_name, "rw": role_ws, "l": user_login, "ws": ws}).first()
        if in_role:
            return True
        # 检查用户所在组是否在该角色中
        group_in_role = db.execute(text(
            "SELECT 1 FROM role_usergroup rug "
            "JOIN usergroupmapping m ON rug.usergroup_id = m.groupname "
            "WHERE rug.role_name = :rn AND rug.role_workspace_id = :rw "
            "AND m.login = :l LIMIT 1"
        ), {"rn": role_name, "rw": role_ws, "l": user_login}).first()
        return group_in_role is not None

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
            "title": row[9] if len(row) > 9 and row[9] else "",
            "instructions": row[4] if len(row) > 4 and row[4] else "",
            "status": STATUS_MAP.get(row[7]) if len(row) > 7 else None,
            "worker": worker or {},
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
            "worker": worker or {},
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
                     activity_step: int = None, task_num: int = None,
                     skip_potential_worker_check: bool = False):
        from sqlalchemy import text

        # 取实际 wf_id/step/num
        if workflow_id is not None and activity_step is not None and task_num is not None:
            wf_id, step, num = workflow_id, activity_step, task_num
        else:
            t_info = db.execute(text(
                "SELECT workflow_id, activity_step, num FROM task WHERE num = :id LIMIT 1"
            ), {"id": task_id}).first()
            if not t_info:
                raise EntityNotFoundException("TaskNotFoundException", str(task_id))
            wf_id, step, num = t_info[0], t_info[1], t_info[2]

        # 权限检查：获取当前 task 状态和指派人
        t_cur = db.execute(text(
            "SELECT status, worker_login FROM task "
            "WHERE workflow_id = :wf_id AND activity_step = :step AND num = :num LIMIT 1"
        ), {"wf_id": wf_id, "step": step, "num": num}).first()
        if not t_cur:
            raise EntityNotFoundException("TaskNotFoundException",
                                          f"{wf_id}-{step}-{num}")
        cur_status, cur_worker = t_cur[0], t_cur[1]
        if cur_status != 1:
            raise NotAllowedException("NotAllowedException40")
        if cur_worker != user_login:
            if not self._is_admin(db, user_login):
                raise NotAllowedException("NotAllowedException40")

        # isPotentialWorker 检查：用户必须是指定角色的成员
        if not skip_potential_worker_check:
            if not self._is_potential_worker(db, ws, user_login, wf_id, step, num):
                raise NotAllowedException("NotAllowedException41")

        status = 2 if action.upper() == "APPROVE" else 3
        db.execute(text(
            "UPDATE task SET status = :s, closurecomment = :c, "
            "signature = :sig, closuredate = NOW() "
            "WHERE workflow_id = :wf_id AND activity_step = :step AND num = :num"
        ), {"s": status, "c": comment, "sig": signature,
            "wf_id": wf_id, "step": step, "num": num})

        # 审批通过时：推进活动（start next tasks）
        if action.upper() == "APPROVE":
            self._advance_activity(db, ws, wf_id, step, num, user_login)

        # 拒绝时：relaunchWorkflow（abort + clone + new workflow）
        relaunched = None
        if action.upper() == "REJECT":
            relaunched = self._relaunch_workflow(db, ws, wf_id, step, num)

        holder_type = None
        holder_reference = None
        holder_version = None
        if relaunched:
            holder_type = relaunched.get("holderType")
            holder_reference = relaunched.get("holderReference")
            holder_version = relaunched.get("holderVersion")
        else:
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

    def _advance_activity(self, db: Session, ws: str, wf_id: int,
                           step: int, completed_num: int, user_login: str):
        """审批通过后推进活动：根据 tasksToComplete 启动下一批 tasks。"""
        from sqlalchemy import text
        # 获取当前活动的 tasksToComplete 配置
        activity = db.execute(text(
            "SELECT tasksToComplete FROM activity WHERE workflow_id = :wf_id AND step = :step"
        ), {"wf_id": wf_id, "step": step}).first()
        if not activity:
            return
        ttc = activity[0] or 0
        # 统计当前活动已审批的任务数
        approved_cnt = db.scalar(text(
            "SELECT COUNT(*) FROM task "
            "WHERE workflow_id = :wf_id AND activity_step = :step AND status = 2"
        ), {"wf_id": wf_id, "step": step}) or 0
        running_cnt = db.scalar(text(
            "SELECT COUNT(*) FROM task "
            "WHERE workflow_id = :wf_id AND activity_step = :step AND status = 1"
        ), {"wf_id": wf_id, "step": step}) or 0
        if approved_cnt >= ttc:
            # 当前活动已完成，所有剩余 running task 重置，启动下一个活动
            db.execute(text(
                "UPDATE task SET status = 0 "
                "WHERE workflow_id = :wf_id AND activity_step = :step AND status = 1"
            ), {"wf_id": wf_id, "step": step})
            self._start_activity(db, ws, wf_id, step + 1)
        elif running_cnt == 0 and approved_cnt < ttc:
            # 没有 running task 且未完成 — 启动足够数量的 task
            pending = db.execute(text(
                "SELECT num FROM task WHERE workflow_id = :wf_id "
                "AND activity_step = :step AND status = 0 ORDER BY num LIMIT :limit"
            ), {"wf_id": wf_id, "step": step, "limit": ttc - approved_cnt}).fetchall()
            for (tnum,) in pending:
                db.execute(text(
                    "UPDATE task SET status = 1, startdate = NOW() "
                    "WHERE workflow_id = :wf_id AND activity_step = :step AND num = :num"
                ), {"wf_id": wf_id, "step": step, "num": tnum})

    def _start_activity(self, db: Session, ws: str, wf_id: int, step: int):
        """启动指定活动的第一个 batch tasks."""
        from sqlalchemy import text
        activity = db.execute(text(
            "SELECT taskstocomplete FROM activity WHERE workflow_id = :wf_id AND step = :step"
        ), {"wf_id": wf_id, "step": step}).first()
        if not activity:
            return
        ttc = activity[0] or 1
        pending = db.execute(text(
            "SELECT num FROM task WHERE workflow_id = :wf_id "
            "AND activity_step = :step AND status = 0 ORDER BY num LIMIT :limit"
        ), {"wf_id": wf_id, "step": step, "limit": ttc}).fetchall()
        for (tnum,) in pending:
            db.execute(text(
                "UPDATE task SET status = 1, startdate = NOW() "
                "WHERE workflow_id = :wf_id AND activity_step = :step AND num = :num"
            ), {"wf_id": wf_id, "step": step, "num": tnum})

    def _relaunch_workflow(self, db: Session, ws: str,
                            wf_id: int, step: int, num: int) -> dict | None:
        """拒绝时 relaunch：abort 当前工作流 + 基于原 model 创建新工作流。"""
        from sqlalchemy import text
        # 查找当前工作流对应的 workflow model（通过活动匹配）
        model_row = db.execute(text(
            "SELECT DISTINCT wm.id, wm.workspace_id FROM workflowmodel wm "
            "JOIN activitymodel am ON wm.id = am.workflowmodel_id AND wm.workspace_id = am.workspace_id "
            "JOIN activity a ON am.step = a.step "
            "WHERE a.workflow_id = :wf_id LIMIT 1"
        ), {"wf_id": wf_id}).first()
        if not model_row:
            return None
        model_id = model_row[0]
        model_ws = model_row[1] or ws

        # 查找 holder（文档/零件/工作区工作流）
        holder_part = db.execute(text(
            "SELECT partmaster_partnumber, version FROM partrevision "
            "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
        ), {"wf_id": wf_id, "ws": ws}).first()
        relinked = None
        if holder_part:
            pm, ver = holder_part[0], holder_part[1]
            # 记录 aborted workflow 关联
            db.execute(text(
                "INSERT INTO part_aborted_workflow "
                "(partmaster_partnumber, partmaster_workspace_id, "
                "partrevision_version, workflow_id) "
                "VALUES (:pn, :ws, :v, :wf_id)"
            ), {"pn": pm, "ws": ws, "v": ver, "wf_id": wf_id})
            # abort 当前工作流
            db.execute(text(
                "UPDATE workflow SET aborteddate = NOW() WHERE id = :id"
            ), {"id": wf_id})
            # 实例化新工作流
            role_mapping = {}
            old_workers = db.execute(text(
                "SELECT DISTINCT worker_login, worker_workspace_id "
                "FROM task WHERE workflow_id = :wf_id AND worker_login IS NOT NULL"
            ), {"wf_id": wf_id}).fetchall()
            for ow in old_workers:
                if ow[0]:
                    task_roles = db.execute(text(
                        "SELECT tm.role_name, tm.role_workspace_id FROM taskmodel tm "
                        "JOIN activitymodel am ON tm.activitymodel_id = am.id "
                        "WHERE am.workflowmodel_id = :mid AND am.workspace_id = :mws "
                        "AND tm.role_name IS NOT NULL"
                    ), {"mid": model_id, "mws": model_ws}).fetchall()
                    for tr in task_roles:
                        role_key = f"{tr[1]}:{tr[0]}"
                        role_mapping[role_key] = ow[0]
            new_inst = self.instantiate_workflow(db, ws, model_id, role_mapping)
            new_wf_id = new_inst["workflowId"]
            # 重关联零件
            db.execute(text(
                "UPDATE partrevision SET workflow_id = :new_id "
                "WHERE workspace_id = :ws AND partmaster_partnumber = :pn AND version = :v"
            ), {"new_id": new_wf_id, "ws": ws, "pn": pm, "v": ver})
            relinked = {"holderType": "part", "holderReference": pm, "holderVersion": ver}
        else:
            holder_doc = db.execute(text(
                "SELECT documentmaster_id, version FROM documentrevision "
                "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
            ), {"wf_id": wf_id, "ws": ws}).first()
            if holder_doc:
                dm, ver = holder_doc[0], holder_doc[1]
                db.execute(text(
                    "UPDATE workflow SET aborteddate = NOW() WHERE id = :id"
                ), {"id": wf_id})
                role_mapping = {}
                old_workers = db.execute(text(
                    "SELECT DISTINCT worker_login, worker_workspace_id "
                    "FROM task WHERE workflow_id = :wf_id AND worker_login IS NOT NULL"
                ), {"wf_id": wf_id}).fetchall()
                for ow in old_workers:
                    if ow[0]:
                        task_roles = db.execute(text(
                            "SELECT tm.role_name, tm.role_workspace_id FROM taskmodel tm "
                            "JOIN activitymodel am ON tm.activitymodel_id = am.id "
                            "WHERE am.workflowmodel_id = :mid AND am.workspace_id = :mws "
                            "AND tm.role_name IS NOT NULL"
                        ), {"mid": model_id, "mws": model_ws}).fetchall()
                        for tr in task_roles:
                            role_key = f"{tr[1]}:{tr[0]}"
                            role_mapping[role_key] = ow[0]
                new_inst = self.instantiate_workflow(db, ws, model_id, role_mapping)
                new_wf_id = new_inst["workflowId"]
                db.execute(text(
                    "UPDATE documentrevision SET workflow_id = :new_id "
                    "WHERE workspace_id = :ws AND documentmaster_id = :dm AND version = :v"
                ), {"new_id": new_wf_id, "ws": ws, "dm": dm, "v": ver})
                relinked = {"holderType": "document", "holderReference": dm,
                            "holderVersion": ver}
            else:
                ww = db.execute(text(
                    "SELECT id FROM workspace_workflow "
                    "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
                ), {"wf_id": wf_id, "ws": ws}).first()
                if ww:
                    db.execute(text(
                        "UPDATE workflow SET aborteddate = NOW() WHERE id = :id"
                    ), {"id": wf_id})
                    role_mapping = {}
                    old_workers = db.execute(text(
                        "SELECT DISTINCT worker_login, worker_workspace_id "
                        "FROM task WHERE workflow_id = :wf_id AND worker_login IS NOT NULL"
                    ), {"wf_id": wf_id}).fetchall()
                    for ow in old_workers:
                        if ow[0]:
                            task_roles = db.execute(text(
                                "SELECT tm.role_name, tm.role_workspace_id FROM taskmodel tm "
                                "JOIN activitymodel am ON tm.activitymodel_id = am.id "
                                "WHERE am.workflowmodel_id = :mid AND am.workspace_id = :mws "
                                "AND tm.role_name IS NOT NULL"
                            ), {"mid": model_id, "mws": model_ws}).fetchall()
                            for tr in task_roles:
                                role_key = f"{tr[1]}:{tr[0]}"
                                role_mapping[role_key] = ow[0]
                    new_inst = self.instantiate_workflow(db, ws, model_id, role_mapping)
                    new_wf_id = new_inst["workflowId"]
                    db.execute(text(
                        "UPDATE workspace_workflow SET workflow_id = :new_id WHERE id = :wwid"
                    ), {"new_id": new_wf_id, "wwid": ww[0]})
                    relinked = {"holderType": "workspace-workflow",
                                "holderReference": ww[0]}
        return relinked

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
