from sqlalchemy.orm import Session
from datetime import datetime
from app.models.workflow import WorkflowModel, Activity, Task, Workflow
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityNotFoundException,
    EntityConstraintException,
)


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
                     final_state: str) -> WorkflowModel:
        m = self.get_model(db, ws, model_id)
        m.finalLifecycleState = final_state
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

    def get_task(self, db: Session, ws: str, task_id: int) -> Task:
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
