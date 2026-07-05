from sqlalchemy.orm import Session
from datetime import datetime
from app.models.workflow import WorkflowModel, Activity, Task, Workflow
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
                     final_state: str, user_login: str) -> WorkflowModel:
        existing = db.query(WorkflowModel).filter(
            WorkflowModel.id == model_id, WorkflowModel.workspace_id == ws).first()
        if existing:
            raise EntityAlreadyExistsException("WorkflowModelAlreadyExistsException", model_id)
        m = WorkflowModel(id=model_id, workspace_id=ws,
                          finalLifecycleState=final_state,
                          creationdate=datetime.utcnow(),
                          author_login=user_login, author_workspace_id=ws)
        db.add(m)
        db.commit()
        db.refresh(m)
        return m

    def update_model(self, db: Session, ws: str, model_id: str,
                     final_state: str,
                     activity_models: list = None) -> WorkflowModel:
        m = self.get_model(db, ws, model_id)
        m.finalLifecycleState = final_state
        # activityModels 关联的是 Workflow 实例（activity/task 表通过 workflow_id 关联），
        # 模板编辑时还没有 Workflow 实例，MVP 策略：暂不持久化 activityModels，
        # 由 router 层在响应中回显前端发来的 activities
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
        return rows

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
        db.commit()


workflow_service = WorkflowService()
