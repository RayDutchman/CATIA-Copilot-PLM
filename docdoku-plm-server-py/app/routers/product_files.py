"""产品实例文件端点（ProductInstanceBinaryResource）。

P2-10: vault 路径与 URL 前缀对齐 Java：
  Java URL:  /files/{ws}/product-instances/{ciId}/{sn}/iterations/{it}[/{fn}]
  Java vault: {ws}/product-instances/{sn}/iterations/{it}/{fn}
  （ciId 仅用于 URL 路由 & 鉴权，不写入 vault 路径）
旧格式 products/{ci_id}/instances/ 已废弃，存量无 DB 记录（prdinstiteration_binres=0行），
唯一旧文件 vault/GD50/products/ceshi/instances/SMOKE-SN-B4/iterations/1/smoke.txt 为孤立文件。
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services import vault as vault_svc
from datetime import datetime, timezone

router = APIRouter()


@router.post("/files/{ws}/product-instances/{ci_id}/{sn}/iterations/{it}", status_code=201)
@router.post("/files/{ws}/product-instances/{ci_id}/{sn}/iterations/{it}/", status_code=201, include_in_schema=False)
def upload(ws: str, ci_id: str, sn: str, it: int,
           upload: UploadFile = File(...),
           current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    data = upload.file.read()
    filename = upload.filename or "unnamed"
    now = datetime.now(timezone.utc)
    content_length = len(data)

    # vault 路径对齐 Java: {ws}/product-instances/{sn}/iterations/{it}/{filename}
    # ci_id 仅参与 URL 路由，不写入 vault/DB 路径
    path = vault_svc.product_instance_iteration_path(ws, sn, it, filename)
    vault_svc.write_file(path, data)

    fullname = vault_svc.product_instance_iteration_fullname(ws, sn, it, filename)

    existing = db.execute(text(
        "SELECT fullname FROM binaryresource WHERE fullname=:fn"
    ), {"fn": fullname}).first()
    if existing:
        db.execute(text(
            "UPDATE binaryresource SET contentlength=:len, lastmodified=:now "
            "WHERE fullname=:fn"
        ), {"len": content_length, "now": now, "fn": fullname})
    else:
        db.execute(text(
            "INSERT INTO binaryresource (fullname, contentlength, lastmodified) "
            "VALUES (:fn, :len, :now)"
        ), {"fn": fullname, "len": content_length, "now": now})

    dup = db.execute(text(
        "SELECT 1 FROM prdinstiteration_binres "
        "WHERE prdinstancemaster_serialnumber=:sn "
        "AND configurationitem_id=:ci AND workspace_id=:ws "
        "AND iteration=:it AND attachedfile_fullname=:fn "
        "LIMIT 1"
    ), {"sn": sn, "ci": ci_id, "ws": ws, "it": it, "fn": fullname}).first()
    if not dup:
        db.execute(text(
            "INSERT INTO prdinstiteration_binres "
            "(prdinstancemaster_serialnumber, configurationitem_id, workspace_id, "
            "iteration, attachedfile_fullname) "
            "VALUES (:sn, :ci, :ws, :it, :fn)"
        ), {"sn": sn, "ci": ci_id, "ws": ws, "it": it, "fn": fullname})

    db.commit()
    return {"fullName": fullname, "name": filename}


@router.get("/files/{ws}/product-instances/{ci_id}/{sn}/iterations/{it}/{fn}")
@router.get("/files/{ws}/product-instances/{ci_id}/{sn}/iterations/{it}/{fn}/", include_in_schema=False)
def download(ws: str, ci_id: str, sn: str, it: int, fn: str,
             current_user: Account = Depends(get_current_user)):
    try:
        path = vault_svc.product_instance_iteration_path(ws, sn, it, fn)
        data = vault_svc.read_file(path)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{fn}"',
            "Cache-Control": "max-age=86400",
            "Last-Modified": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "ETag": f'"{fn}_{len(data)}"',
        })

