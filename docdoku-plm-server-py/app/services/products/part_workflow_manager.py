"""PartWorkflowManager——零件工作流审批/拒绝。

对齐 Java PartWorkflowManagerBean。
"""
from sqlalchemy.orm import Session
from app.core.exceptions import NotAllowedException


class PartWorkflowService:
    """零件工作流管理。"""

    def get_current_workflow(self, db: Session, ws: str, part_number: str,
                              version: str) -> dict:
        """获取零件修订版的当前工作流。"""
        from sqlalchemy import text
        wf = db.execute(text(
            "SELECT w.* FROM workflow w "
            "JOIN partrevision pr ON w.id = pr.workflow_id "
            "WHERE pr.workspace_id = :ws AND pr.partmaster_partnumber = :pn "
            "AND pr.version = :ver LIMIT 1"
        ), {"ws": ws, "pn": part_number, "ver": version}).first()
        if not wf:
            from app.core.exceptions import WorkflowNotFoundException
            raise WorkflowNotFoundException("WorkflowNotFoundException",
                f"{ws}/{part_number}/{version}")
        return {"id": wf[0], "final_lifecyclestate": wf[1] if len(wf) > 1 else None,
                "aborted": bool(wf[2]) if len(wf) > 2 else False}

    def get_aborted_workflows(self, db: Session, ws: str, part_number: str,
                               version: str) -> list:
        """获取零件修订版的所有已中止工作流（part_aborted_workflow 关联表）。"""
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT w.id, w.finallifecyclestate, w.aborteddate FROM workflow w "
            "JOIN part_aborted_workflow paw ON paw.workflow_id = w.id "
            "WHERE paw.partmaster_workspace_id = :ws "
            "AND paw.partmaster_partnumber = :pn "
            "AND paw.partrevision_version = :ver"
        ), {"ws": ws, "pn": part_number, "ver": version}).fetchall()
        return [{"id": r[0], "finalLifeCycleState": r[1],
                 "abortedDate": str(r[2]) if r[2] else None} for r in rows]

    def approve_task_on_part(self, db: Session, ws: str, task_key: dict,
                              part_number: str, version: str,
                              comment: str = "", signature: str = "",
                              user_login: str = ""):
        """批准零件上的任务。"""
        from app.services.task_manager import task_service
        return task_service.process_task(
            db, ws, action="APPROVE", comment=comment, signature=signature,
            user_login=user_login,
            workflow_id=task_key.get("workflow_id"),
            activity_step=task_key.get("activity_step"),
            task_num=task_key.get("task_num"),
        )

    def reject_task_on_part(self, db: Session, ws: str, task_key: dict,
                             part_number: str, version: str,
                             comment: str = "", signature: str = "",
                             user_login: str = ""):
        """拒绝零件上的任务。"""
        from app.services.task_manager import task_service
        return task_service.process_task(
            db, ws, action="REJECT", comment=comment, signature=signature,
            user_login=user_login,
            workflow_id=task_key.get("workflow_id"),
            activity_step=task_key.get("activity_step"),
            task_num=task_key.get("task_num"),
        )


part_workflow_service = PartWorkflowService()
