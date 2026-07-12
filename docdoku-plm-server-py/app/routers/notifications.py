from typing import List
from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.schemas.misc.modification_notification import ModificationNotificationDTO
from app.services.notification_manager import notification_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


@router.get(f"{PREFIX}/notifications", response_model=List[dict])
@router.get(f"{PREFIX}/notifications/", include_in_schema=False)
def list_notifications(ws: str, db: Session = Depends(get_db),
                       current_user: Account = Depends(get_current_user)):
    """获取当前用户未读通知列表。"""
    notifications = notification_service.list_for_user(db, ws, current_user.login)
    return [notification_service.build_notification_dto(n, db) for n in notifications]


@router.put(f"{PREFIX}/notifications/{{notification_id}}", response_model=ModificationNotificationDTO)
@router.put(f"{PREFIX}/notifications/{{notification_id}}/", include_in_schema=False)
def acknowledge_notification(ws: str, notification_id: int, body: dict = Body(...),
                             db: Session = Depends(get_db),
                             current_user: Account = Depends(get_current_user)):
    n = notification_service.acknowledge(
        db, ws, notification_id,
        body.get("ackComment", ""), current_user.login)
    return notification_service.build_notification_dto(n, db)
