"""Task 管理服务——对标 Payara TaskManagerBean。

从 workflow_manager.py 拆出任务查询、审批、推进逻辑。
"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.auth import Account
from app.core.exceptions import (
    NotAllowedException, TaskNotFoundException, WorkflowNotFoundException,
)

STATUS_MAP = {0: "NOT_STARTED", 1: "IN_PROGRESS", 2: "APPROVED", 3: "REJECTED"}


class TaskService:

    def _is_admin(self, db: Session, login: str) -> bool:
        return db.execute(text(
            "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
        ), {"l": login}).first() is not None

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
            raise TaskNotFoundException("TaskNotFoundException", str(task_id or task_num))
        return row

    def get_assigned_tasks(self, db: Session, ws: str, login: str) -> list:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT DISTINCT t.* FROM task t "
            "LEFT JOIN task_user tu ON t.workflow_id=tu.workflow_id "
            "AND t.activity_step=tu.activity_step "
            "AND t.num=tu.task_num "
            "LEFT JOIN task_usergroup tug ON t.workflow_id=tug.workflow_id "
            "AND t.activity_step=tug.activity_step "
            "AND t.num=tug.task_num "
            "LEFT JOIN usergroupmapping ugm ON tug.usergroup_id=ugm.groupname "
            "WHERE t.status < 2 "
            "AND (tu.user_login=:l AND tu.user_workspace_id=:w "
            "     OR (ugm.login=:l AND tug.usergroup_workspace_id=:w))"
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
                holder_type = "documents"
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

    def _is_potential_worker(self, db: Session, ws: str, user_login: str,
                               workflow_id: int, activity_step: int, task_num: int) -> bool:
        """检查用户是否在 task_user 或 task_usergroup 中（对齐 Java Task.isPotentialWorker）。"""
        # 先检查 TASK_USER（直接分配的用户）
        user = db.execute(text(
            "SELECT 1 FROM task_user "
            "WHERE workflow_id=:wf AND activity_step=:step AND task_num=:num "
            "AND user_login=:login AND user_workspace_id=:ws LIMIT 1"
        ), {"wf": workflow_id, "step": activity_step, "num": task_num,
            "login": user_login, "ws": ws}).first()
        if user:
            return True
        # 通过 TASK_USERGROUP + usergroupmapping（检查组中用户）
        group = db.execute(text(
            "SELECT 1 FROM task_usergroup tug "
            "JOIN usergroupmapping ugm ON tug.usergroup_id = ugm.groupname "
            "WHERE tug.workflow_id=:wf AND tug.activity_step=:step "
            "AND tug.task_num=:num "
            "AND ugm.login=:login AND tug.usergroup_workspace_id=:ws LIMIT 1"
        ), {"wf": workflow_id, "step": activity_step, "num": task_num,
            "login": user_login, "ws": ws}).first()
        return group is not None

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
                raise TaskNotFoundException("TaskNotFoundException", str(task_id))
            wf_id, step, num = t_info[0], t_info[1], t_info[2]

        # 检查工作流是否存在
        wf_exists = db.execute(text(
            "SELECT 1 FROM workflow WHERE id = :id LIMIT 1"
        ), {"id": wf_id}).first()
        if not wf_exists:
            raise WorkflowNotFoundException("WorkflowNotFoundException", str(wf_id))

        # 权限检查：获取当前 task 状态和指派人
        t_cur = db.execute(text(
            "SELECT status, worker_login FROM task "
            "WHERE workflow_id = :wf_id AND activity_step = :step AND num = :num LIMIT 1"
        ), {"wf_id": wf_id, "step": step, "num": num}).first()
        if not t_cur:
            raise TaskNotFoundException("TaskNotFoundException",
                                          f"{wf_id}-{step}-{num}")
        cur_status, cur_worker = t_cur[0], t_cur[1]
        if cur_status != 1:
            raise NotAllowedException("NotAllowedException40")
        if cur_worker is not None and cur_worker != user_login:
            raise NotAllowedException("NotAllowedException40")

        # isPotentialWorker 检查：用户必须是 TASK_USER/TASK_USERGROUP 中分配的角色成员
        if not skip_potential_worker_check:
            if not self._is_potential_worker(db, ws, user_login, wf_id, step, num):
                raise NotAllowedException("NotAllowedException41")

        status = 2 if action.upper() == "APPROVE" else 3
        db.execute(text(
            "UPDATE task SET status = :s, worker_login = :wl, worker_workspace_id = :wws, "
            "closurecomment = :c, signature = :sig, closuredate = NOW() "
            "WHERE workflow_id = :wf_id AND activity_step = :step AND num = :num"
        ), {"s": status, "wl": user_login, "wws": ws, "c": comment, "sig": signature,
            "wf_id": wf_id, "step": step, "num": num})

        # 审批通过时：推进活动（start next tasks）
        workflow_completed = False
        if action.upper() == "APPROVE":
            workflow_completed = self._advance_activity(db, ws, wf_id, step, num, user_login)

        # 工作流全部活动完成时：更新持有者的生命周期状态
        if workflow_completed:
            self._apply_final_lifecycle_state(db, ws, wf_id)

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
                holder_type = "documents"
                holder_reference = doc[0]
                holder_version = doc[1]
            else:
                part = db.execute(text(
                    "SELECT partmaster_partnumber, version FROM partrevision "
                    "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
                ), {"wf_id": wf_id, "ws": ws}).first()
                if part:
                    holder_type = "part"
                    holder_reference = part[0]
                    holder_version = part[1]
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
                           step: int, completed_num: int, user_login: str) -> bool:
        """审批通过后推进活动：根据 tasksToComplete 启动下一批 tasks。
        
        Sequential 类型严格顺序执行，每次只启动一个 task。
        返回 True 表示工作流已全部完成（当前活动完成后无下一活动）。
        """
        from sqlalchemy import text
        # 获取当前活动的 tasksToComplete 和 dtype
        activity = db.execute(text(
            "SELECT tasksToComplete, dtype FROM activity WHERE workflow_id = :wf_id AND step = :step"
        ), {"wf_id": wf_id, "step": step}).first()
        if not activity:
            return False
        ttc = activity[0] or 0
        dtype = activity[1] if len(activity) > 1 else ""
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
            if not self._start_activity(db, ws, wf_id, step + 1):
                # 下一活动不存在 → 工作流全部完成
                return True
        elif running_cnt == 0 and approved_cnt < ttc:
            # 没有 running task 且未完成 — Sequential 每次只启动一个 task
            limit = 1 if dtype == "SEQUENTIAL" else ttc - approved_cnt
            pending = db.execute(text(
                "SELECT num FROM task WHERE workflow_id = :wf_id "
                "AND activity_step = :step AND status = 0 ORDER BY num LIMIT :limit"
            ), {"wf_id": wf_id, "step": step, "limit": limit}).fetchall()
            for (tnum,) in pending:
                db.execute(text(
                    "UPDATE task SET status = 1, startdate = NOW() "
                    "WHERE workflow_id = :wf_id AND activity_step = :step AND num = :num"
                ), {"wf_id": wf_id, "step": step, "num": tnum})
        return False

    def _start_activity(self, db: Session, ws: str, wf_id: int, step: int) -> bool:
        """启动指定活动的第一个 batch tasks。
        
        Sequential 类型每次只启动一个 task。
        返回 True 表示有活动被启动，False 表示 step 超出范围（工作流完成）。
        """
        from sqlalchemy import text
        activity = db.execute(text(
            "SELECT taskstocomplete, dtype FROM activity WHERE workflow_id = :wf_id AND step = :step"
        ), {"wf_id": wf_id, "step": step}).first()
        if not activity:
            return False
        ttc = activity[0] or 1
        dtype = activity[1] if len(activity) > 1 else ""
        limit = 1 if dtype == "SEQUENTIAL" else ttc
        pending = db.execute(text(
            "SELECT num FROM task WHERE workflow_id = :wf_id "
            "AND activity_step = :step AND status = 0 ORDER BY num LIMIT :limit"
        ), {"wf_id": wf_id, "step": step, "limit": limit}).fetchall()
        for (tnum,) in pending:
            db.execute(text(
                "UPDATE task SET status = 1, startdate = NOW() "
                "WHERE workflow_id = :wf_id AND activity_step = :step AND num = :num"
            ), {"wf_id": wf_id, "step": step, "num": tnum})
        return True

    def _apply_final_lifecycle_state(self, db: Session, ws: str, wf_id: int):
        """工作流全部活动完成时，将 workflow.finallifecyclestate 同步到持有者 revision 的 status 列。
        
        对齐 Java：Workflow.getLifeCycleState() 完成时返回 finalLifeCycleState，
        持有者 PartRevision/DocumentRevision 的 getLifeCycleState() 委托给 workflow。
        本方法将 finalLifeCycleState 映射为 revision status 整数值并持久化到 DB。
        """
        from sqlalchemy import text
        wf = db.execute(text(
            "SELECT finallifecyclestate FROM workflow WHERE id = :id"
        ), {"id": wf_id}).first()
        if not wf or not wf[0]:
            return
        final_lcs = wf[0].upper()
        # finalLifeCycleState → status 映射（对齐 Java PartRevision/DocumentRevision 的 lifecycle）
        status_map = {"RELEASED": 1, "OBSOLETE": 2}
        new_status = status_map.get(final_lcs)
        if new_status is None:
            # TODO: 当前仅处理 RELEASED / OBSOLETE，更复杂的 lifecycle 字符串映射后续扩展
            return
        # 更新零件 revision
        db.execute(text(
            "UPDATE partrevision SET status = :s "
            "WHERE workflow_id = :wf_id AND workspace_id = :ws"
        ), {"s": new_status, "wf_id": wf_id, "ws": ws})
        # 更新文档 revision
        db.execute(text(
            "UPDATE documentrevision SET status = :s "
            "WHERE workflow_id = :wf_id AND workspace_id = :ws"
        ), {"s": new_status, "wf_id": wf_id, "ws": ws})

    def _relaunch_workflow(self, db: Session, ws: str,
                            wf_id: int, step: int, num: int) -> dict | None:
        """拒绝时 relaunch：深拷贝原 workflow + abort 旧的。"""
        from sqlalchemy import text

        # 1. 查找 holder 类型（文档/零件/workspace_workflow）
        holder_type = None
        holder_ref = None
        holder_ver = None
        holder_ww_id = None

        part = db.execute(text(
            "SELECT partmaster_partnumber, version FROM partrevision "
            "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
        ), {"wf_id": wf_id, "ws": ws}).first()
        if part:
            holder_type = "part"
            holder_ref, holder_ver = part[0], part[1]
        else:
            doc = db.execute(text(
                "SELECT documentmaster_id, version FROM documentrevision "
                "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
            ), {"wf_id": wf_id, "ws": ws}).first()
            if doc:
                holder_type = "documents"
                holder_ref, holder_ver = doc[0], doc[1]
            else:
                ww = db.execute(text(
                    "SELECT id FROM workspace_workflow "
                    "WHERE workflow_id = :wf_id AND workspace_id = :ws LIMIT 1"
                ), {"wf_id": wf_id, "ws": ws}).first()
                if ww:
                    holder_type = "workspace-workflow"
                    holder_ref = ww[0]
                    holder_ww_id = ww[0]
                else:
                    return None

        # 2. 深拷贝原 workflow（先拷贝再 abort，保留原始状态快照）
        new_wf = db.execute(text(
            "INSERT INTO workflow (aborteddate, finallifecyclestate) "
            "SELECT NULL, finallifecyclestate FROM workflow WHERE id = :old_id "
            "RETURNING id"
        ), {"old_id": wf_id}).first()
        new_wf_id = new_wf[0]

        db.execute(text(
            "INSERT INTO activity (step, dtype, lifecyclestate, workflow_id, taskstocomplete) "
            "SELECT step, dtype, lifecyclestate, :new_id, taskstocomplete "
            "FROM activity WHERE workflow_id = :old_id"
        ), {"new_id": new_wf_id, "old_id": wf_id})

        db.execute(text(
            "INSERT INTO task (num, title, instructions, duration, status, "
            "worker_login, worker_workspace_id, activity_step, workflow_id, targetiteration) "
            "SELECT num, title, instructions, duration, status, "
            "worker_login, worker_workspace_id, activity_step, :new_id, targetiteration "
            "FROM task WHERE workflow_id = :old_id"
        ), {"new_id": new_wf_id, "old_id": wf_id})

        # 复制 TASK_USER / TASK_USERGROUP（关联到新 workflow）
        db.execute(text(
            "INSERT INTO task_user (task_num, activity_step, workflow_id, user_login, user_workspace_id) "
            "SELECT task_num, activity_step, :new_id, user_login, user_workspace_id "
            "FROM task_user WHERE workflow_id = :old_id"
        ), {"new_id": new_wf_id, "old_id": wf_id})
        db.execute(text(
            "INSERT INTO task_usergroup (task_num, activity_step, workflow_id, usergroup_id, usergroup_workspace_id) "
            "SELECT task_num, activity_step, :new_id, usergroup_id, usergroup_workspace_id "
            "FROM task_usergroup WHERE workflow_id = :old_id"
        ), {"new_id": new_wf_id, "old_id": wf_id})

        # 3. kill 旧 workflow 上的 running tasks + abort 旧 workflow
        db.execute(text(
            "UPDATE task SET status = 3 WHERE workflow_id = :wf_id AND status = 1"
        ), {"wf_id": wf_id})
        db.execute(text(
            "UPDATE workflow SET aborteddate = NOW() WHERE id = :id"
        ), {"id": wf_id})

        # 4. 清理旧 workflow 的 relaunch 关联
        db.execute(text(
            "DELETE FROM activity_relaunch WHERE activity_workflow_id = :wf_id"
        ), {"wf_id": wf_id})

        # 5. 归档旧 workflow
        if holder_type == "part":
            db.execute(text(
                "INSERT INTO part_aborted_workflow "
                "(partmaster_partnumber, partmaster_workspace_id, "
                "partrevision_version, workflow_id) "
                "VALUES (:pn, :ws, :v, :wf_id)"
            ), {"pn": holder_ref, "ws": ws, "v": holder_ver, "wf_id": wf_id})
        elif holder_type == "documents":
            db.execute(text(
                "INSERT INTO document_aborted_workflow "
                "(documentmaster_id, documentmaster_workspace_id, "
                "documentrevision_version, workflow_id) "
                "VALUES (:dm, :ws, :v, :wf_id)"
            ), {"dm": holder_ref, "ws": ws, "v": holder_ver, "wf_id": wf_id})
        elif holder_type == "workspace-workflow":
            db.execute(text(
                "INSERT INTO workspace_aborted_workflow "
                "(workspace_workflow_id, workspace_workflow_workspace_id, workflow_id) "
                "VALUES (:wwid, :ws, :wf_id)"
            ), {"wwid": holder_ww_id, "ws": ws, "wf_id": wf_id})

        # 6. 重关联 holder 到新 workflow
        if holder_type == "part":
            db.execute(text(
                "UPDATE partrevision SET workflow_id = :new_id "
                "WHERE workspace_id = :ws AND partmaster_partnumber = :pn AND version = :v"
            ), {"new_id": new_wf_id, "ws": ws, "pn": holder_ref, "v": holder_ver})
        elif holder_type == "documents":
            db.execute(text(
                "UPDATE documentrevision SET workflow_id = :new_id "
                "WHERE workspace_id = :ws AND documentmaster_id = :dm AND version = :v"
            ), {"new_id": new_wf_id, "ws": ws, "dm": holder_ref, "v": holder_ver})
        elif holder_type == "workspace-workflow":
            db.execute(text(
                "UPDATE workspace_workflow SET workflow_id = :new_id WHERE id = :wwid"
            ), {"new_id": new_wf_id, "wwid": holder_ww_id})

        # 7. relaunch：重置从指定 step 开始的 tasks，然后启动第一批
        db.execute(text(
            "UPDATE task SET status = 0, worker_login = NULL, worker_workspace_id = NULL, "
            "startdate = NULL, closuredate = NULL, "
            "closurecomment = NULL, signature = NULL "
            "WHERE workflow_id = :wf_id AND activity_step >= :step"
        ), {"wf_id": new_wf_id, "step": step})
        self._start_activity(db, ws, new_wf_id, step)

        return {"holderType": holder_type,
                "holderReference": holder_ref,
                "holderVersion": holder_ver}

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


task_service = TaskService()
