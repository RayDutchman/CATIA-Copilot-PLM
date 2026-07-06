"""产品配置（ProductConfiguration）端点路由。"""
from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.product import ProductConfiguration
from app.services.product_structure import ProductStructureService
from app.services.acl_helper import apply_acl
from app.schemas.product import ProductConfigurationDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
svc = ProductStructureService()

_NAME_CACHE: dict = {}


def _get_user_dto(db: Session, login: str, ws: str) -> dict:
    if not login:
        return {"login": "", "name": "", "email": None, "language": None, "workspaceId": ws}
    if login in _NAME_CACHE:
        cached = _NAME_CACHE[login]
        return {"login": login, "name": cached, "email": None, "language": None, "workspaceId": ws}
    from app.models.auth import Account
    acc = db.query(Account).filter(Account.login == login).first()
    name = acc.name if (acc and acc.name) else login
    _NAME_CACHE[login] = name
    return {"login": login, "name": name, "email": None, "language": None, "workspaceId": ws}


def _fmt_date(d) -> str | None:
    if d is None:
        return None
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"


def _build_acl(db: Session, acl_id: int) -> dict | None:
    if not acl_id or not db:
        return None
    from app.models.security import ACL, AclUserEntry, AclUserGroupEntry
    acl = db.query(ACL).filter(ACL.id == acl_id).first()
    if not acl:
        return None
    user_entries = db.query(AclUserEntry).filter(AclUserEntry.acl_id == acl_id).all()
    group_entries = db.query(AclUserGroupEntry).filter(AclUserGroupEntry.acl_id == acl_id).all()
    _PERM = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}
    return {
        "userEntries": [
            {"key": e.principal_login, "value": _PERM.get(e.permission, "FORBIDDEN")}
            for e in user_entries
        ],
        "groupEntries": [
            {"key": e.principal_id, "value": _PERM.get(e.permission, "FORBIDDEN")}
            for e in group_entries
        ],
        "userEntriesMap": {e.principal_login: _PERM.get(e.permission, "FORBIDDEN") for e in user_entries},
        "userGroupEntriesMap": {},
    }


def _config_to_dict(cfg, db) -> dict:
    ws = cfg.configurationitem_workspace_id
    return {
        "id": cfg.id,
        "name": cfg.name,
        "configurationItemId": cfg.configurationitem_id,
        "description": cfg.description or "",
        "author": _get_user_dto(db, cfg.author_login, ws),
        "acl": _build_acl(db, cfg.acl_id) or {},
        "creationDate": _fmt_date(cfg.creation_date),
        "substituteLinks": [],
        "optionalUsageLinks": [],
        "substitutesParts": [],
        "optionalsParts": [],
    }


# ── product-configurations ──

@router.post("/workspaces/{ws}/product-configurations", status_code=201)
def create_workspace_config(ws: str, body: dict,
                             current_user: Account = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """workspace 级创建配置，CI ID 从请求体获取（对应 Java POST /workspaces/{ws}/product-configurations）。"""
    ci_id = body.get("configurationItemId", "")
    cfg = svc.create_config(db, ws, ci_id, body.get("name", ""),
                              body.get("description", ""), current_user.login,
                              body.get("substituteLinks"),
                              body.get("optionalUsageLinks"),
                              body.get("userEntries"),
                              body.get("groupEntries"))
    return {"id": cfg.id, "name": cfg.name}


@router.get("/workspaces/{ws}/product-configurations", response_model=List[ProductConfigurationDTO])
@router.get("/workspaces/{ws}/product-configurations/", include_in_schema=False)
def list_configs(ws: str, current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    configs = svc.list_configs(db, ws)
    return [{"id": c.id, "name": c.name,
             "configurationItemId": c.configurationitem_id,
             "description": c.description or "",
             "author": _get_user_dto(db, c.author_login, ws),
             "acl": _build_acl(db, c.acl_id) or {},
             "creationDate": _fmt_date(c.creation_date),
             "substituteLinks": [],
             "optionalUsageLinks": [],
             "substitutesParts": [],
             "optionalsParts": [],}
            for c in configs]


@router.get("/workspaces/{ws}/product-configurations/{pid}/configurations", response_model=List[ProductConfigurationDTO])
@router.get("/workspaces/{ws}/product-configurations/{pid}/configurations/", include_in_schema=False)
def list_ci_configs(ws: str, pid: str,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    configs = svc.list_configs(db, ws, pid)
    return [{"id": c.id, "name": c.name,
             "configurationItemId": c.configurationitem_id,
             "description": c.description or "",
             "author": _get_user_dto(db, c.author_login, ws),
             "acl": _build_acl(db, c.acl_id) or {},
             "creationDate": _fmt_date(c.creation_date),
             "substituteLinks": [],
             "optionalUsageLinks": [],
             "substitutesParts": [],
             "optionalsParts": [],}
            for c in configs]



@router.get("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}", response_model=ProductConfigurationDTO)
@router.get("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}/", include_in_schema=False)
def get_config_by_ci(ws: str, ciId: str, cfg_id: int,
                     db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    cfg = db.query(ProductConfiguration).filter(
        ProductConfiguration.id == cfg_id,
        ProductConfiguration.configurationitem_id == ciId,
        ProductConfiguration.configurationitem_workspace_id == ws,
    ).first()
    if not cfg:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("ProductConfigurationNotFoundException", str(cfg_id))
    return _config_to_dict(cfg, db)


@router.delete("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}", status_code=204)
@router.delete("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}/", status_code=204, include_in_schema=False)
def delete_config_by_ci(ws: str, ciId: str, cfg_id: int,
                        db: Session = Depends(get_db),
                        current_user: Account = Depends(get_current_user)):
    cfg = db.query(ProductConfiguration).filter(
        ProductConfiguration.id == cfg_id,
        ProductConfiguration.configurationitem_id == ciId,
        ProductConfiguration.configurationitem_workspace_id == ws,
    ).first()
    if not cfg:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("ProductConfigurationNotFoundException", str(cfg_id))
    svc.delete_config(db, ws, cfg_id)
    return Response(status_code=204)


# ── products/{ci_id}/configurations ──

@router.post("/workspaces/{ws}/products/{ci_id}/configurations", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/configurations/", status_code=201, include_in_schema=False)
def create_config(ws: str, ci_id: str, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    cfg = svc.create_config(db, ws, ci_id, body.get("name", ""),
                              body.get("description", ""), current_user.login,
                              body.get("substituteLinks"),
                              body.get("optionalUsageLinks"),
                              body.get("userEntries"),
                              body.get("groupEntries"))
    return {"id": cfg.id, "name": cfg.name}


@router.delete("/workspaces/{ws}/products/{ci_id}/configurations/{cfg_id}")
@router.delete("/workspaces/{ws}/products/{ci_id}/configurations/{cfg_id}/", include_in_schema=False)
def delete_config(ws: str, ci_id: str, cfg_id: int,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    svc.delete_config(db, ws, cfg_id)
    return {"status": "deleted"}


@router.put("/workspaces/{ws}/products/{ci_id}/configurations/{cfg_id}/acl")
@router.put("/workspaces/{ws}/products/{ci_id}/configurations/{cfg_id}/acl/", include_in_schema=False)
def update_config_acl(ws: str, ci_id: str, cfg_id: int, body: dict,
                      db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    config = db.query(ProductConfiguration).filter(
        ProductConfiguration.configurationitem_workspace_id == ws,
        ProductConfiguration.configurationitem_id == ci_id,
        ProductConfiguration.id == cfg_id,
    ).first()
    if not config:
        from app.core.exceptions import EntityNotFoundException
        raise EntityNotFoundException("ProductConfigurationNotFoundException", str(cfg_id))
    user_entries = body.get("userEntries", {})
    group_entries = body.get("groupEntries", {})
    if not user_entries and not group_entries:
        config.acl_id = None
        db.commit()
        return {"aclId": None}
    acl_id = getattr(config, "acl_id", None)
    new_acl_id = apply_acl(db, acl_id, user_entries, group_entries)
    if config.acl_id != new_acl_id:
        config.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}


@router.post("/workspaces/{ws}/products/{pid}/path-to-path-links", status_code=201)
def create_path_to_path_link(ws: str, pid: str, body: dict,
                              current_user: Account = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """创建路径间链接 stub。"""
    return {"id": -1, "status": "stub"}
