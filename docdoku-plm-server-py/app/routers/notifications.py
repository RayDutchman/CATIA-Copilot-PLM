from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.notification_service import notification_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


@router.put(f"{PREFIX}/notifications/{{notification_id}}")
@router.put(f"{PREFIX}/notifications/{{notification_id}}/", include_in_schema=False)
def acknowledge_notification(ws: str, notification_id: int, body: dict = Body(...),
                             db: Session = Depends(get_db),
                             current_user: Account = Depends(get_current_user)):
    n = notification_service.acknowledge(
        db, ws, notification_id,
        body.get("ackComment", ""), current_user.login)
    return {"id": n.id, "acknowledged": n.acknowledged}
