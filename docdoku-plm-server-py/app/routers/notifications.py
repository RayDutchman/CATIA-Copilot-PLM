from typing import List
from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.notification_manager import notification_service
from app.schemas.misc import ModificationNotificationDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _build_notification_dict(n, db: Session) -> dict:
    """构建完整 ModificationNotificationDTO 响应。"""
    result = {
        "id": n.id,
        "acknowledged": n.acknowledged,
        "impactedPartNumber": n.impacted_partmaster_partnumber,
        "impactedPartVersion": n.impacted_partrevision_version,
        "modifiedPartNumber": n.modified_partmaster_partnumber,
        "modifiedPartVersion": n.modified_partrevision_version,
        "modifiedPartIteration": n.modified_iteration or 0,
        "ackComment": n.acknowledgementcomment or "",
        "ackAuthor": {},
        "author": {},
    }
    if n.acknowledgementdate:
        result["ackDate"] = int(n.acknowledgementdate.timestamp() * 1000)
    else:
        result["ackDate"] = None
    if n.ackauthor_login:
        ack = db.execute(text(
            "SELECT login, name, email FROM account WHERE login = :l"
        ), {"l": n.ackauthor_login}).fetchone()
        result["ackAuthor"] = {"login": ack[0], "name": ack[1], "email": ack[2]} if ack else {"login": n.ackauthor_login}
    else:
        result["ackAuthor"] = {}

    # 查询 modified part 的 author/checkInDate/iterationNote/name
    if n.modified_workspace_id and n.modified_partmaster_partnumber:
        pm = db.execute(text(
            "SELECT name FROM partmaster WHERE partnumber = :pn AND workspace_id = :ws"
        ), {"pn": n.modified_partmaster_partnumber, "ws": n.modified_workspace_id}).fetchone()
        result["modifiedPartName"] = pm[0] if pm else None
        pi = db.execute(text(
            "SELECT author_login, checkindate, iterationnote FROM partiteration "
            "WHERE workspace_id = :ws AND partmaster_partnumber = :pn "
            "AND partrevision_version = :v AND iteration = :iter"
        ), {
            "ws": n.modified_workspace_id,
            "pn": n.modified_partmaster_partnumber,
            "v": n.modified_partrevision_version,
            "iter": n.modified_iteration,
        }).fetchone()
        if pi:
            author_login = pi[0]
            checkindate = pi[1]
            iteration_note = pi[2]
            if author_login:
                au = db.execute(text(
                    "SELECT login, name, email FROM account WHERE login = :l"
                ), {"l": author_login}).fetchone()
                result["author"] = {"login": au[0], "name": au[1], "email": au[2]} if au else {"login": author_login}
            else:
                result["author"] = {}
            result["checkInDate"] = int(checkindate.timestamp() * 1000) if checkindate else None
            result["iterationNote"] = iteration_note or ""
        else:
            result["author"] = {}
            result["checkInDate"] = None
            result["iterationNote"] = ""
    else:
        result["modifiedPartName"] = None
        result["author"] = {}
        result["checkInDate"] = None
        result["iterationNote"] = ""
    return result


@router.put(f"{PREFIX}/notifications/{{notification_id}}", response_model=ModificationNotificationDTO)
@router.put(f"{PREFIX}/notifications/{{notification_id}}/", include_in_schema=False)
def acknowledge_notification(ws: str, notification_id: int, body: dict = Body(...),
                             db: Session = Depends(get_db),
                             current_user: Account = Depends(get_current_user)):
    n = notification_service.acknowledge(
        db, ws, notification_id,
        body.get("ackComment", ""), current_user.login)
    return _build_notification_dict(n, db)


@router.get(f"{PREFIX}/notifications", response_model=List[ModificationNotificationDTO])
@router.get(f"{PREFIX}/notifications/", include_in_schema=False)
def list_notifications(ws: str, db: Session = Depends(get_db),
                       current_user: Account = Depends(get_current_user)):
    """返回工作区所有修改通知（按时间倒序）。"""
    notifications = notification_service.list_all(db, ws)
    return [_build_notification_dict(n, db) for n in notifications]

