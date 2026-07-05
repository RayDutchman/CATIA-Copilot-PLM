from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import EntityNotFoundException
from app.models.auth import Account
from app.models.workflow import Webhook, WebhookApp

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _webhook_to_dict(w, app=None) -> dict:
    return {
        "id": w.id,
        "name": w.name,
        "workspaceId": w.workspace_id,
        "active": w.active,
        "webhookApp": {
            "id": app.id if app else w.webhookapp_id,
            "dtype": app.dtype if app else None,
            "uri": app.uri if app else None,
            "method": app.method if app else None,
        } if app or w.webhookapp_id else None,
    }


@router.get(f"{PREFIX}/webhooks")
@router.get(f"{PREFIX}/webhooks/", include_in_schema=False)
def list_webhooks(ws: str, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    hooks = db.query(Webhook).filter(Webhook.workspace_id == ws).all()
    return [_webhook_to_dict(h) for h in hooks]


@router.get(f"{PREFIX}/webhooks/{{webhook_id}}")
@router.get(f"{PREFIX}/webhooks/{{webhook_id}}/", include_in_schema=False)
def get_webhook(ws: str, webhook_id: int, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    w = db.query(Webhook).filter(Webhook.id == webhook_id,
                                  Webhook.workspace_id == ws).first()
    if not w:
        raise EntityNotFoundException("WebhookNotFoundException", str(webhook_id))
    return _webhook_to_dict(w)


@router.post(f"{PREFIX}/webhooks", status_code=201)
@router.post(f"{PREFIX}/webhooks/", status_code=201, include_in_schema=False)
def create_webhook(ws: str, body: dict, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
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


@router.put(f"{PREFIX}/webhooks/{{webhook_id}}")
@router.put(f"{PREFIX}/webhooks/{{webhook_id}}/", include_in_schema=False)
def update_webhook(ws: str, webhook_id: int, body: dict, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    w = db.query(Webhook).filter(Webhook.id == webhook_id,
                                  Webhook.workspace_id == ws).first()
    if not w:
        raise EntityNotFoundException("WebhookNotFoundException", str(webhook_id))
    if "name" in body:
        w.name = body["name"]
    if "active" in body:
        w.active = body["active"]
    db.commit()
    db.refresh(w)
    return _webhook_to_dict(w)

