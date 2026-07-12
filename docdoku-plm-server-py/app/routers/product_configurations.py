"""产品配置（ProductConfiguration）端点路由。"""
from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.product_structure import ProductStructureService
from app.services.factory.acl_factory import build_acl_dict
from app.models.util.date_utils import format_iso_date
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
    dto = svc._build_user_dto(db, login, ws)
    _NAME_CACHE[login] = dto.get("name", login)
    return dto


def _decode_paths(db: Session, ws: str, ci_id: str, paths: list) -> list:
    """每个 path → LightPartLinkListDTO{partLinks:[...]}（对齐 Java decodePath）。"""
    result = []
    for path in paths:
        if not path:
            continue
        try:
            part_links = svc.decode_path(db, ws, ci_id, path)
        except Exception:
            part_links = []
        result.append({"partLinks": part_links})
    return result


def _config_to_dict(cfg, db) -> dict:
    ws = cfg.configurationitem_workspace_id
    sub_paths = svc.get_config_substitute_paths(db, cfg.id)
    opt_paths = svc.get_config_optional_paths(db, cfg.id)
    return {
        "id": cfg.id,
        "name": cfg.name,
        "configurationItemId": cfg.configurationitem_id,
        "description": cfg.description or "",
        "author": _get_user_dto(db, cfg.author_login, ws),
        "acl": build_acl_dict(db, cfg.acl_id) or {},
        "creationDate": format_iso_date(cfg.creation_date),
        "substituteLinks": sub_paths,
        "optionalUsageLinks": opt_paths,
        "substitutesParts": _decode_paths(db, ws, cfg.configurationitem_id, sub_paths),
        "optionalsParts": _decode_paths(db, ws, cfg.configurationitem_id, opt_paths),
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
    return [_config_to_dict(c, db) for c in configs]


@router.get("/workspaces/{ws}/product-configurations/{pid}/configurations", response_model=List[ProductConfigurationDTO])
@router.get("/workspaces/{ws}/product-configurations/{pid}/configurations/", include_in_schema=False)
def list_ci_configs(ws: str, pid: str,
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    configs = svc.list_configs(db, ws, pid)
    return [_config_to_dict(c, db) for c in configs]



@router.get("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}", response_model=ProductConfigurationDTO)
@router.get("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}/", include_in_schema=False)
def get_config_by_ci(ws: str, ciId: str, cfg_id: int,
                     db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    cfg = svc.get_config_by_id(db, ws, ciId, cfg_id)
    return _config_to_dict(cfg, db)


@router.delete("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}", status_code=204)
@router.delete("/workspaces/{ws}/product-configurations/{ciId}/configurations/{cfg_id}/", status_code=204, include_in_schema=False)
def delete_config_by_ci(ws: str, ciId: str, cfg_id: int,
                        db: Session = Depends(get_db),
                        current_user: Account = Depends(get_current_user)):
    svc.get_config_by_id(db, ws, ciId, cfg_id)
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


@router.delete("/workspaces/{ws}/products/{ci_id}/configurations/{cfg_id}", status_code=204)
@router.delete("/workspaces/{ws}/products/{ci_id}/configurations/{cfg_id}/", status_code=204, include_in_schema=False)
def delete_config(ws: str, ci_id: str, cfg_id: int,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    svc.delete_config(db, ws, cfg_id)
    return Response(status_code=204)


@router.put("/workspaces/{ws}/products/{ci_id}/configurations/{cfg_id}/acl")
@router.put("/workspaces/{ws}/products/{ci_id}/configurations/{cfg_id}/acl/", include_in_schema=False)
def update_config_acl(ws: str, ci_id: str, cfg_id: int, body: dict,
                      db: Session = Depends(get_db),
                      current_user: Account = Depends(get_current_user)):
    user_entries = body.get("userEntries", {})
    group_entries = body.get("groupEntries", {})
    return svc.update_config_acl(db, ws, ci_id, cfg_id, user_entries, group_entries)


# 注意：CI 级 PathToPathLink CRUD（POST/GET/PUT/DELETE）定义在 products.py 路由中，
# 避免与 product_configurations.py 的同 prefix 路由冲突。
