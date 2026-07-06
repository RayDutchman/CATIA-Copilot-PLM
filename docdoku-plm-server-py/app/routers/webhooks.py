from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException, EntityNotFoundException
from app.models.auth import Account
from app.models.workflow import Webhook, WebhookApp
from app.schemas.misc import WebhookDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _check_is_admin_or_workspace_admin(db: Session, ws: str, current_user: Account):
    """验证当前用户是全局管理员或工作区管理员，否则 403。"""
    is_global_admin = db.execute(text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first()
    if is_global_admin:
        return
    is_ws_admin = db.execute(text(
        "SELECT 1 FROM workspace WHERE id=:w AND admin_login=:l"
    ), {"w": ws, "l": current_user.login}).first()
    if not is_ws_admin:
        raise AccessRightException("AccessRightException")


def _appname_from_dtype(dtype: str | None) -> str:
    if dtype == "AWS_SNS":
        return "SNSWEBHOOK"
    return "SIMPLEWEBHOOK"


def _webhook_to_dict(w, app=None) -> dict:
    app_dtype = app.dtype if app else None
    return {
        "id": w.id,
        "name": w.name,
        "workspaceId": w.workspace_id,
        "active": w.active,
        "appName": _appname_from_dtype(app_dtype),
        "parameters": [],
        "webhookApp": {
            "id": app.id if app else w.webhookapp_id,
            "dtype": app.dtype if app else None,
            "uri": app.uri if app else None,
            "method": app.method if app else None,
        } if app or w.webhookapp_id else {},
    }


@router.get(f"{PREFIX}/webhooks", response_model=List[WebhookDTO])
@router.get(f"{PREFIX}/webhooks/", include_in_schema=False)
def list_webhooks(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    hooks = db.query(Webhook).filter(Webhook.workspace_id == ws).all()
    return [_webhook_to_dict(h) for h in hooks]


@router.get(f"{PREFIX}/webhooks/{{webhook_id}}", response_model=WebhookDTO)
@router.get(f"{PREFIX}/webhooks/{{webhook_id}}/", include_in_schema=False)
def get_webhook(ws: str, webhook_id: int, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    w = db.query(Webhook).filter(Webhook.id == webhook_id,
                                  Webhook.workspace_id == ws).first()
    if not w:
        raise EntityNotFoundException("WebhookNotFoundException", str(webhook_id))
    return _webhook_to_dict(w)


@router.post(f"{PREFIX}/webhooks", status_code=201, response_model=WebhookDTO)
@router.post(f"{PREFIX}/webhooks/", status_code=201, include_in_schema=False)
def create_webhook(ws: str, body: dict, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    _check_is_admin_or_workspace_admin(db, ws, current_user)
    app_data = body.get("webhookApp", {})
    app = WebhookApp(dtype=app_data.get("dtype", "SIMPLE_HTTP"),
                     uri=app_data.get("uri", ""),
                     method=app_data.get("method", "POST"),
                     auth=app_data.get("auth"))
    db.add(app)
    db.flush()
    w = Webhook(name=body.get("name", ""), workspace_id=ws,
                active=body.get("active", True), webhookapp_id=app.id)
    db.add(w)
    db.commit()
    db.refresh(w)
    return _webhook_to_dict(w, app)


@router.delete(f"{PREFIX}/webhooks/{{webhook_id}}", status_code=204)
@router.delete(f"{PREFIX}/webhooks/{{webhook_id}}/", status_code=204, include_in_schema=False)
def delete_webhook(ws: str, webhook_id: int, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    _check_is_admin_or_workspace_admin(db, ws, current_user)
    w = db.query(Webhook).filter(Webhook.id == webhook_id,
                                  Webhook.workspace_id == ws).first()
    if w:
        app_id = w.webhookapp_id
        db.delete(w)
        db.flush()
        if app_id:
            app = db.query(WebhookApp).filter(WebhookApp.id == app_id).first()
            if app:
                db.delete(app)
        db.commit()


@router.put(f"{PREFIX}/webhooks/{{webhook_id}}", response_model=WebhookDTO)
@router.put(f"{PREFIX}/webhooks/{{webhook_id}}/", include_in_schema=False)
def update_webhook(ws: str, webhook_id: int, body: dict, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    _check_is_admin_or_workspace_admin(db, ws, current_user)
    w = db.query(Webhook).filter(Webhook.id == webhook_id,
                                  Webhook.workspace_id == ws).first()
    if not w:
        raise EntityNotFoundException("WebhookNotFoundException", str(webhook_id))
    if "name" in body:
        w.name = body["name"]
    if "active" in body:
        w.active = body["active"]
    app_data = body.get("webhookApp", {})
    app = None
    if app_data:
        app = db.query(WebhookApp).filter(WebhookApp.id == w.webhookapp_id).first()
        if app:
            if "method" in app_data:
                app.method = app_data["method"]
            if "uri" in app_data:
                app.uri = app_data["uri"]
    db.commit()
    db.refresh(w)
    if app:
        db.refresh(app)
    return _webhook_to_dict(w, app)

