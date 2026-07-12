from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_workspace_admin
from app.models.auth import Account
from app.schemas.misc import WebhookDTO
from app.services.webhook_manager import webhook_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


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
                  _admin: Account = Depends(require_workspace_admin)):

    hooks = webhook_service.list_webhooks(db, ws)
    return [_webhook_to_dict(w, app) for w, app in hooks]


@router.get(f"{PREFIX}/webhooks/{{webhook_id}}", response_model=WebhookDTO)
@router.get(f"{PREFIX}/webhooks/{{webhook_id}}/", include_in_schema=False)
def get_webhook(ws: str, webhook_id: int, db: Session = Depends(get_db),
                _admin: Account = Depends(require_workspace_admin)):

    w, app = webhook_service.get_webhook(db, ws, webhook_id)
    return _webhook_to_dict(w, app)


@router.post(f"{PREFIX}/webhooks", status_code=201, response_model=WebhookDTO)
@router.post(f"{PREFIX}/webhooks/", status_code=201, include_in_schema=False)
def create_webhook(ws: str, body: dict, db: Session = Depends(get_db),
                   _admin: Account = Depends(require_workspace_admin)):

    w, app = webhook_service.create_webhook(
        db, ws,
        name=body.get("name", ""),
        active=body.get("active", True),
        app_data=body.get("webhookApp", {}),
    )
    return _webhook_to_dict(w, app)


@router.delete(f"{PREFIX}/webhooks/{{webhook_id}}", status_code=204)
@router.delete(f"{PREFIX}/webhooks/{{webhook_id}}/", status_code=204, include_in_schema=False)
def delete_webhook(ws: str, webhook_id: int, db: Session = Depends(get_db),
                   _admin: Account = Depends(require_workspace_admin)):

    webhook_service.delete_webhook(db, ws, webhook_id)


@router.put(f"{PREFIX}/webhooks/{{webhook_id}}", response_model=WebhookDTO)
@router.put(f"{PREFIX}/webhooks/{{webhook_id}}/", include_in_schema=False)
def update_webhook(ws: str, webhook_id: int, body: dict, db: Session = Depends(get_db),
                   _admin: Account = Depends(require_workspace_admin)):

    w, app = webhook_service.update_webhook(db, ws, webhook_id, body)
    return _webhook_to_dict(w, app)
