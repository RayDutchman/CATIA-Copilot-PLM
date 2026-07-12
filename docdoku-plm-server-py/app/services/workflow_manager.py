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
                            user_login: str, workspace_id: str | None = None) -> None:
        from app.services.factory.acl_factory import check_write_access
        if not check_write_access(db, acl_id, user_login, self._is_admin(db, user_login),
                                  workspace_id=workspace_id):
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
        step_to_id = {}  # {step: activitymodel_id}，用于 relaunchStep 两步解析
        relaunch_info = []  # [(activitymodel_id, relaunch_step)]
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
                step_to_id[am.get("step", 0)] = am_obj.id
                relaunch_step = am.get("relaunchStep")
                if relaunch_step is not None:
                    relaunch_info.append((am_obj.id, relaunch_step))
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
            # 写入 activitymodel_relaunch 表（对齐 Java extractActivityModelFromDTO）
            for am_id, relaunch_step in relaunch_info:
                target_am_id = step_to_id.get(relaunch_step)
                if target_am_id is not None:
                    db.execute(text(
                        "INSERT INTO activitymodel_relaunch (activitymodel_id, relaunchactivitymodel_id) "
                        "VALUES (:am_id, :target_id)"
                    ), {"am_id": am_id, "target_id": target_am_id})
        db.commit()
        db.refresh(m)
        return m

    def update_model(self, db: Session, ws: str, model_id: str,
                     final_state: str,
                     activity_models: list = None,
                     user_login: str = None) -> WorkflowModel:
        m = self.get_model(db, ws, model_id)
        if user_login:
            self._check_write_access(db, m.acl_id, user_login, workspace_id=ws)
        m.finalLifecycleState = final_state
        if activity_models is not None:
            # 先清旧 relaunch 行（FK 无 CASCADE，需在删 ActivityModel 前清理）
            db.execute(text(
                "DELETE FROM activitymodel_relaunch WHERE activitymodel_id IN ("
                "SELECT id FROM activitymodel WHERE workflowmodel_id = :mid AND workspace_id = :ws)"
            ), {"mid": model_id, "ws": ws})
            # 删除旧 ActivityModel（级联删除旧 TaskModel）
            db.query(ActivityModel).filter(
                ActivityModel.workflowmodel_id == model_id,
                ActivityModel.workspace_id == ws,
            ).delete()
            step_to_id = {}
            relaunch_info = []
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
                step_to_id[am.get("step", 0)] = am_obj.id
                relaunch_step = am.get("relaunchStep")
                if relaunch_step is not None:
                    relaunch_info.append((am_obj.id, relaunch_step))
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
            # 写入 activitymodel_relaunch 表（对齐 Java extractActivityModelFromDTO）
            for am_id, relaunch_step in relaunch_info:
                target_am_id = step_to_id.get(relaunch_step)
                if target_am_id is not None:
                    db.execute(text(
                        "INSERT INTO activitymodel_relaunch (activitymodel_id, relaunchactivitymodel_id) "
                        "VALUES (:am_id, :target_id)"
                    ), {"am_id": am_id, "target_id": target_am_id})
        db.commit()
        db.refresh(m)
        return m

    def delete_model(self, db: Session, ws: str, model_id: str,
                     user_login: str = None):
        m = self.get_model(db, ws, model_id)
        if user_login:
            self._check_write_access(db, m.acl_id, user_login, workspace_id=ws)
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
        """对齐 Java getWorkspaceWorkflowList：查 workspace_workflow 表返回 UUID id。"""
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT ww.id, w.aborteddate, w.finallifecyclestate "
            "FROM workspace_workflow ww "
            "JOIN workflow w ON ww.workflow_id = w.id "
            "WHERE ww.workspace_id = :ws"
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
                                       workflow_id: int) -> list:
        """对齐 Java getWorkflowAbortedWorkflowList：
        按 workflow_id 定位持有者（document/part/workspace_workflow），
        返回该持有者名下所有 aborteddate IS NOT NULL 的 workflow 列表。"""
        from sqlalchemy import text

        # 1) 检查是否为 document 的 workflow
        dr = db.execute(text(
            "SELECT workspace_id, documentmaster_id, version "
            "FROM documentrevision WHERE workflow_id = :wid"
        ), {"wid": workflow_id}).first()
        if dr:
            rows = db.execute(text(
                "SELECT w.id, w.aborteddate, w.finallifecyclestate "
                "FROM workflow w "
                "JOIN document_aborted_workflow daw ON w.id = daw.workflow_id "
                "WHERE daw.documentmaster_workspace_id = :ws "
                "AND daw.documentmaster_id = :mid "
                "AND daw.documentrevision_version = :v "
                "AND w.aborteddate IS NOT NULL"
            ), {"ws": dr[0], "mid": dr[1], "v": dr[2]}).fetchall()
            return [{"id": r[0], "abortedDate": str(r[1]) if r[1] else None,
                     "finalLifecycleState": r[2]} for r in rows]

        # 2) 检查是否为 part 的 workflow
        pr = db.execute(text(
            "SELECT workspace_id, partmaster_partnumber, version "
            "FROM partrevision WHERE workflow_id = :wid"
        ), {"wid": workflow_id}).first()
        if pr:
            rows = db.execute(text(
                "SELECT w.id, w.aborteddate, w.finallifecyclestate "
                "FROM workflow w "
                "JOIN part_aborted_workflow paw ON w.id = paw.workflow_id "
                "WHERE paw.partmaster_workspace_id = :ws "
                "AND paw.partmaster_partnumber = :pn "
                "AND paw.partrevision_version = :v "
                "AND w.aborteddate IS NOT NULL"
            ), {"ws": pr[0], "pn": pr[1], "v": pr[2]}).fetchall()
            return [{"id": r[0], "abortedDate": str(r[1]) if r[1] else None,
                     "finalLifecycleState": r[2]} for r in rows]

        # 3) 检查是否为 workspace_workflow 的 workflow
        ww = db.execute(text(
            "SELECT id, workspace_id FROM workspace_workflow WHERE workflow_id = :wid"
        ), {"wid": workflow_id}).first()
        if ww:
            rows = db.execute(text(
                "SELECT w.id, w.aborteddate, w.finallifecyclestate "
                "FROM workflow w "
                "JOIN workspace_aborted_workflow waw ON w.id = waw.workflow_id "
                "WHERE waw.workspace_workflow_id = :wwid "
                "AND waw.workspace_workflow_workspace_id = :ws "
                "AND w.aborteddate IS NOT NULL"
            ), {"wwid": ww[0], "ws": ww[1]}).fetchall()
            return [{"id": r[0], "abortedDate": str(r[1]) if r[1] else None,
                     "finalLifecycleState": r[2]} for r in rows]

        # 找不到持有者返回空列表
        return []

    # ========== workspace_workflow 实例化与管理 ==========

    def _normalize_role_mapping(self, role_mapping: dict) -> dict:
        """规范化 role_mapping，兼容旧格式 {role_key: user_login} 和新格式 {role_key: {"users": [...], "groups": [...]}}"""
        if not role_mapping:
            return {}
        normalized = {}
        for role_key, value in role_mapping.items():
            if isinstance(value, dict):
                normalized[role_key] = {
                    "users": value.get("users", []) or [],
                    "groups": value.get("groups", []) or [],
                }
            elif isinstance(value, str):
                normalized[role_key] = {"users": [value], "groups": []}
            elif isinstance(value, list):
                normalized[role_key] = {"users": value, "groups": []}
        return normalized

    def instantiate_workflow(self, db: Session, ws: str, model_id: str,
                              role_mapping: dict = None) -> dict:
        """从 workflow_model 实例化 workspace_workflow"""
        from sqlalchemy import text
        if role_mapping is None:
            role_mapping = {}
        normalized_mapping = self._normalize_role_mapping(role_mapping)
        wm = self.get_model(db, ws, model_id)
        ams = db.query(ActivityModel).filter(
            ActivityModel.workflowmodel_id == model_id,
            ActivityModel.workspace_id == ws,
        ).order_by(ActivityModel.step).all()
        if not ams:
            raise EntityNotFoundException("ActivityModelNotFoundException", model_id)
        # 创建 workflow 实例（用 RETURNING id 避免 currval 并发风险）
        wf_row = db.execute(text(
            "INSERT INTO workflow (aborteddate, finallifecyclestate) VALUES (NULL, :fls) RETURNING id"
        ), {"fls": wm.finalLifecycleState or ""}).fetchone()
        wf_id = wf_row[0]
        # 创建 activities 和 tasks，worker 创建时为 NULL（审批时才写入）
        created_tasks = []  # 记录创建了哪些 task，用于后续 TASK_USER/TASK_USERGROUP 写入
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
                db.execute(text(
                    "INSERT INTO task (num, activity_step, workflow_id, title, instructions, "
                    "status, worker_login, worker_workspace_id, duration) "
                    "VALUES (:num, :step, :wf_id, :title, :instructions, "
                    "0, NULL, NULL, :dur)"
                ), {"num": tm.num, "step": am.step, "wf_id": wf_id,
                    "title": tm.title or "", "instructions": tm.instructions or "",
                     "dur": tm.duration})
                created_tasks.append((tm.num, am.step, wf_id,
                                       tm.role_name, tm.role_workspace_id))
        # INSERT TASK_USER / TASK_USERGROUP（对齐 Java Task.assignedUsers + assignedGroups）
        for task_num, task_step, wf, role_name, role_ws in created_tasks:
            if not role_name:
                continue
            role_key = f"{role_ws or ws}:{role_name}"
            mapping = normalized_mapping.get(role_key, {})
            if not mapping:
                # fallback: 直接匹配 role_name（兼容只传 role_name 作为 key 的情况）
                mapping = normalized_mapping.get(role_name, {})
            for user_login in mapping.get("users", []):
                db.execute(text(
                    "INSERT INTO task_user (task_num, activity_step, workflow_id, "
                    "user_login, user_workspace_id) "
                    "VALUES (:num, :step, :wf, :login, :uws)"
                ), {"num": task_num, "step": task_step, "wf": wf,
                    "login": user_login, "uws": ws})
            for group_id in mapping.get("groups", []):
                db.execute(text(
                    "INSERT INTO task_usergroup (task_num, activity_step, workflow_id, "
                    "usergroup_id, usergroup_workspace_id) "
                    "VALUES (:num, :step, :wf, :gid, :gws)"
                ), {"num": task_num, "step": task_step, "wf": wf,
                    "gid": group_id, "gws": ws})
        # 检查每个有角色定义的 task 至少有一个 potential worker（对齐 Java task.hasPotentialWorker()）
        for task_num, task_step, wf, role_name, role_ws in created_tasks:
            if not role_name:
                continue
            has = db.execute(text(
                "SELECT 1 FROM task_user "
                "WHERE workflow_id=:wf AND activity_step=:step AND task_num=:num "
                "UNION ALL "
                "SELECT 1 FROM task_usergroup "
                "WHERE workflow_id=:wf AND activity_step=:step AND task_num=:num "
                "LIMIT 1"
            ), {"wf": wf, "step": task_step, "num": task_num}).first()
            if not has:
                raise NotAllowedException("NotAllowedException56")
        # 获取 step-0 activity 的 dtype，Sequential 只启动第 1 个 task
        dtype_row = db.execute(text(
            "SELECT dtype FROM activity WHERE workflow_id = :wf_id AND step = 0"
        ), {"wf_id": wf_id}).first()
        dtype = dtype_row[0] if dtype_row else ""
        if dtype == "SEQUENTIAL":
            db.execute(text(
                "UPDATE task SET status = 1, startdate = NOW() WHERE id IN ("
                "SELECT id FROM task WHERE workflow_id = :wf_id AND activity_step = 0 "
                "AND status = 0 ORDER BY num LIMIT 1)"
            ), {"wf_id": wf_id})
        else:
            db.execute(text(
                "UPDATE task SET status = 1, startdate = NOW() "
                "WHERE workflow_id = :wf_id AND activity_step = 0 AND status = 0"
            ), {"wf_id": wf_id})
        # 创建 workspace_workflow 记录
        ww_id = str(uuid.uuid4())
        db.execute(text(
            "INSERT INTO workspace_workflow (id, workspace_id, workflow_id) "
            "VALUES (:id, :ws, :wf_id)"
        ), {"id": ww_id, "ws": ws, "wf_id": wf_id})
        db.commit()
        logger.info("Workflow %s instantiated in workspace %s", wf_id, ws)
        # TODO: 缺少审批通知——对齐 Java WorkflowManagerBean.instantiateWorkflow L359
        #   Java 做法：notifier.sendApproval(ws, runningTasks, workspaceWorkflow)
        #     - runningTasks: 当前 status=1 (IN_PROGRESS) 的 task，查询 task 表 WHERE status=1 AND workflow_id=:wf_id
        #     - 遍历每个 runningTask: 取出 worker_login → 查 Account 取 email/language
        #     - 调用 notifier 发审批通知邮件（主题:"审批通知"、含任务标题/说明/workflow 链接）
        #   当前 app/services/notifier.py 仅有 bulk index 通知方法，无 sendApproval。
        #   栈内可用设施:
        #     - SMTP 可用 smtp:1025 (MailHog)，notifier._send_email 可复用
        #     - GCM sender (gcm/gcm_sender.py) 可推送设备通知
        #   待实现（不能改 notifier.py 时最小切入）：
        #     1. 查 runningTasks = db.execute("SELECT t.*, a.account_email FROM task t JOIN task_user tu ... JOIN account a ... WHERE t.status=1 AND t.workflow_id=:wf_id")
        #     2. 逐 task worker 发 SMTP 邮件（复用 notifier._send_email 或 notifier.py 新增 sendApproval）
        #   注意：此通知不是阻塞操作——send 失败只打 log，不影响实例化流程。
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
        db.execute(text("DELETE FROM task_user WHERE workflow_id = :id"), {"id": wf_id})
        db.execute(text("DELETE FROM task_usergroup WHERE workflow_id = :id"), {"id": wf_id})
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
