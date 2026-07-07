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
            raise TaskNotFoundException("TaskNotFoundException", str(task_id or task_num))
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
                holder_type = "documents"
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
        from app.services.workflow_manager import workflow_service

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
            new_inst = workflow_service.instantiate_workflow(db, ws, model_id, role_mapping)
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
                new_inst = workflow_service.instantiate_workflow(db, ws, model_id, role_mapping)
                new_wf_id = new_inst["workflowId"]
                db.execute(text(
                    "UPDATE documentrevision SET workflow_id = :new_id "
                    "WHERE workspace_id = :ws AND documentmaster_id = :dm AND version = :v"
                ), {"new_id": new_wf_id, "ws": ws, "dm": dm, "v": ver})
                relinked = {"holderType": "documents", "holderReference": dm,
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
                    new_inst = workflow_service.instantiate_workflow(db, ws, model_id, role_mapping)
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


task_service = TaskService()
