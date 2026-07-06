"""DocumentWorkflowManager——文档工作流审批/拒绝。

对齐 Java DocumentWorkflowManagerBean。
"""
from sqlalchemy.orm import Session


class DocumentWorkflowService:
    """文档工作流管理。"""

    def get_current_workflow(self, db: Session, ws: str, doc_id: str,
                              version: str) -> dict:
        """获取文档修订版的当前工作流。"""
        from sqlalchemy import text
        wf = db.execute(text(
            "SELECT w.* FROM workflow w "
            "JOIN documentrevision dr ON w.id = dr.workflow_id "
            "WHERE dr.workspace_id = :ws AND dr.documentmaster_id = :did "
            "AND dr.version = :ver LIMIT 1"
        ), {"ws": ws, "did": doc_id, "ver": version}).first()
        if not wf:
            from app.core.exceptions import WorkflowNotFoundException
            raise WorkflowNotFoundException("WorkflowNotFoundException",
                f"{ws}/{doc_id}/{version}")
        return {"id": wf[0]}

    def get_aborted_workflows(self, db: Session, ws: str, doc_id: str,
                               version: str) -> list:
        """获取文档修订版的所有已中止工作流。"""
        return []

    def approve_task_on_document(self, db: Session, ws: str, task_key: dict,
                                   doc_id: str, version: str,
                                   comment: str = "", signature: str = "",
                                   user_login: str = ""):
        """批准文档上的任务。"""
        from app.services.task_manager import task_service
        return task_service.process_task(
            db, ws, action="APPROVE", comment=comment, signature=signature,
            user_login=user_login,
            workflow_id=task_key.get("workflow_id"),
            activity_step=task_key.get("activity_step"),
            task_num=task_key.get("task_num"),
        )

    def reject_task_on_document(self, db: Session, ws: str, task_key: dict,
                                  doc_id: str, version: str,
                                  comment: str = "", signature: str = "",
                                  user_login: str = ""):
        """拒绝文档上的任务。"""
        from app.services.task_manager import task_service
        return task_service.process_task(
            db, ws, action="REJECT", comment=comment, signature=signature,
            user_login=user_login,
            workflow_id=task_key.get("workflow_id"),
            activity_step=task_key.get("activity_step"),
            task_num=task_key.get("task_num"),
        )


document_workflow_service = DocumentWorkflowService()
