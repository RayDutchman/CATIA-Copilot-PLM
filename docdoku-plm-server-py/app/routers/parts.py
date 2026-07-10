"""零件集合路由（PartsResource）。"""
import uuid
import tempfile
import os
from fastapi import APIRouter, Depends, Query, Body, Request, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.part import PartRevision, PartIteration, part_revision_tags
from app.schemas.part import (
    PartRevisionDTO, PartCreationDTO, CountDTO, LightPartMasterDTO,
)
from app.schemas.import_ import ImportDTO
from app.schemas.import_preview import ImportPreviewDTO
from app.services.importer import importer_service
from app.services.importers.import_record import (
    create_import, complete_import, get_import, list_imports, delete_import_record,
)
from app.services.product_manager import ProductService
from app.services.part_mapper import map_revision

router = APIRouter()
svc = ProductService()


@router.get("/workspaces/{workspace_id}/parts", response_model=list[PartRevisionDTO])
def list_parts(
    workspace_id: str,
    start: int = Query(0, ge=0),
    # 对齐 Payara: length=0 表示返回全部（不限量）
    length: int = Query(50, ge=0, le=500),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revisions = svc.list_revisions(db, workspace_id, start, length if length > 0 else None)
    return [map_revision(pr, db) for pr in revisions]


@router.get("/workspaces/{workspace_id}/parts/count", response_model=CountDTO)
def count_parts(
    workspace_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CountDTO(count=svc.count_parts(db, workspace_id))


@router.get("/workspaces/{workspace_id}/parts/numbers",
             response_model=list[LightPartMasterDTO])
def search_numbers(
    workspace_id: str,
    q: str = Query(""),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    masters = svc.search_numbers(db, workspace_id, q)
    return [LightPartMasterDTO(partNumber=m.number, partName=m.name or "") for m in masters]


@router.get("/workspaces/{workspace_id}/parts/checkedout",
             response_model=list[PartRevisionDTO])
def list_checked_out(
    workspace_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revisions = svc.list_checked_out(db, workspace_id)
    return [map_revision(pr, db) for pr in revisions]


@router.get("/workspaces/{workspace_id}/parts/countCheckedOut",
             response_model=CountDTO)
def count_checked_out(
    workspace_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CountDTO(count=len(svc.list_checked_out(db, workspace_id)))


@router.get("/workspaces/{workspace_id}/parts/search",
            response_model=list[PartRevisionDTO])
def search_parts(
    workspace_id: str,
    name: str = Query(None),
    number: str = Query(None),
    type: str = Query(None),
    author: str = Query(None),
    createdAfter: str = Query(None),
    createdBefore: str = Query(None),
    modifiedAfter: str = Query(None),
    modifiedBefore: str = Query(None),
    tags: str = Query(None),
    attributes: str = Query(None),
    content: str = Query(None),
    start: int = Query(0, ge=0, alias="from"),
    length: int = Query(50, ge=0, le=500, alias="size"),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    from app.services.indexer.indexer_query_builder import es_query_builder

    # ES 优先搜索
    try:
        es_params = {"from": start, "size": length}
        if name: es_params["name"] = name
        if number: es_params["number"] = number
        if author: es_params["author"] = author
        if createdAfter: es_params["createdFrom"] = createdAfter
        if createdBefore: es_params["createdTo"] = createdBefore
        if modifiedAfter: es_params["modifiedFrom"] = modifiedAfter
        if modifiedBefore: es_params["modifiedTo"] = modifiedBefore
        if tags: es_params["tags"] = tags
        if content: es_params["content"] = content
        keys = es_query_builder.search_parts(workspace_id, es_params)
        if keys:
            # 解析迭代级 key: '{number}-{version}-{iteration}' → 按 revision 去重
            seen = set()
            rev_keys = []
            for k in keys:
                parts = k.rsplit("-", 2)
                if len(parts) >= 2:
                    nv = (parts[0], parts[1])  # (number, version)
                    if nv not in seen:
                        seen.add(nv)
                        rev_keys.append(nv)
            if rev_keys:
                conditions = [
                    (PartRevision.workspace_id == workspace_id) &
                    (PartRevision.partmaster_partnumber == nv[0]) &
                    (PartRevision.version == nv[1])
                    for nv in rev_keys
                ]
                revisions = db.query(PartRevision).options(
                    joinedload(PartRevision.iterations),
                    joinedload(PartRevision.part_master),
                ).filter(or_(*conditions)).all()
                # 按 ES 返回顺序排列
                rev_map = {(pr.partmaster_partnumber, pr.version): pr for pr in revisions}
                ordered = [rev_map[k] for k in rev_keys if k in rev_map]
                return [map_revision(pr, db) for pr in ordered]
    except Exception:
        pass  # ES 失败 → fallback 到 DB 搜索

    # DB LIKE fallback
    author_val = author if author else None
    ca = datetime.fromisoformat(createdAfter) if createdAfter else None
    cb = datetime.fromisoformat(createdBefore) if createdBefore else None
    ma = datetime.fromisoformat(modifiedAfter) if modifiedAfter else None
    mb = datetime.fromisoformat(modifiedBefore) if modifiedBefore else None
    tag_list = tags.split(",") if tags else None
    attr_list = attributes.split(",") if attributes else None
    revisions = svc.search_parts(
        db, workspace_id,
        name=name, number=number, type_=type, author=author_val,
        created_after=ca, created_before=cb,
        modified_after=ma, modified_before=mb,
        tags=tag_list, attributes=attr_list, content=content,
        start=start, length=length,
    )
    return [map_revision(pr, db) for pr in revisions]


@router.get("/workspaces/{workspace_id}/parts/tags/{tag_id}",
            response_model=list[PartRevisionDTO])
@router.get("/workspaces/{workspace_id}/parts/tags/{tag_id}/",
            response_model=list[PartRevisionDTO], include_in_schema=False)
def get_parts_by_tag(workspace_id: str, tag_id: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    revisions = (
        db.query(PartRevision)
        .join(part_revision_tags,
              (PartRevision.workspace_id == part_revision_tags.c.partmaster_workspace_id)
              & (PartRevision.partmaster_partnumber == part_revision_tags.c.partmaster_partnumber)
              & (PartRevision.version == part_revision_tags.c.partrevision_version))
        .filter(part_revision_tags.c.tag_label == tag_id,
                PartRevision.workspace_id == workspace_id)
        .all()
    )
    return [map_revision(pr, db) for pr in revisions]


@router.get("/workspaces/{workspace_id}/parts/parts_last_iter",
            response_model=list[dict])
@router.get("/workspaces/{workspace_id}/parts/parts_last_iter/",
            response_model=list[dict], include_in_schema=False)
def parts_last_iter(workspace_id: str, q: str = Query(""),
                    current_user: Account = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    subq = (
        db.query(
            PartIteration.workspace_id,
            PartIteration.partmaster_partnumber,
            PartIteration.partrevision_version,
            func.max(PartIteration.iteration).label("max_iter"),
        )
        .filter(PartIteration.workspace_id == workspace_id)
        .group_by(
            PartIteration.workspace_id,
            PartIteration.partmaster_partnumber,
            PartIteration.partrevision_version,
        )
        .subquery()
    )
    rows = (
        db.query(
            PartRevision,
            subq.c.max_iter,
        )
        .join(
            subq,
            (PartRevision.workspace_id == subq.c.workspace_id)
            & (PartRevision.partmaster_partnumber == subq.c.partmaster_partnumber)
            & (PartRevision.version == subq.c.partrevision_version),
        )
        .filter(PartRevision.workspace_id == workspace_id)
    )
    if q:
        rows = rows.filter(
            PartRevision.partmaster_partnumber.ilike(f"%{q}%")
        )
    result = []
    for pr, max_iter in rows.all():
        result.append({
            "workspaceId": pr.workspace_id,
            "partName": pr.part_master.name or "" if pr.part_master else "",
            "partNumber": pr.partmaster_partnumber,
            "partVersion": pr.version,
            "iteration": max_iter,
        })
    return result


@router.post("/workspaces/{workspace_id}/parts",
            response_model=PartRevisionDTO, status_code=201)
@router.post("/workspaces/{workspace_id}/parts/",
            response_model=PartRevisionDTO, status_code=201, include_in_schema=False)
def create_part(
    workspace_id: str,
    body: PartCreationDTO,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pr = svc.create_part(db, workspace_id, current_user.login, body)
    return map_revision(pr, db)


# ── queries stubs ──────────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/parts/queries",
            response_model=list[dict])
@router.get("/workspaces/{workspace_id}/parts/queries/",
            response_model=list[dict], include_in_schema=False)
def get_queries(workspace_id: str,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """列出工作区已保存的自定义查询（对齐 Java getQueries → QueryDTO 列表）。"""
    from sqlalchemy import text
    rows = db.execute(text(
        "SELECT id, name, creationdate, queryrule_id, pathdata_queryrule_id "
        "FROM query WHERE author_workspace_id = :ws ORDER BY id"
    ), {"ws": workspace_id}).fetchall()
    result = []
    for r in rows:
        qid = r[0]
        selects = [s[0] for s in db.execute(text(
            "SELECT selects FROM query_selects WHERE query_id = :q"
        ), {"q": qid}).fetchall()]
        order_by = [s[0] for s in db.execute(text(
            "SELECT orderbylist FROM query_order_by WHERE query_id = :q"
        ), {"q": qid}).fetchall()]
        grouped_by = [s[0] for s in db.execute(text(
            "SELECT groupedbylist FROM query_grouped_by WHERE query_id = :q"
        ), {"q": qid}).fetchall()]
        result.append({
            "id": qid,
            "name": r[1] or "",
            "creationDate": r[2].isoformat() + "Z" if r[2] else None,
            "queryRule": _load_query_rule(db, r[3]),
            "pathDataQueryRule": _load_query_rule(db, r[4]),
            "selects": selects,
            "orderByList": order_by,
            "groupedByList": grouped_by,
            "contexts": _load_query_contexts(db, qid),
        })
    return result


def _load_query_rule(db, rule_id):
    """递归加载 QueryRule 树（对齐 Java QueryRuleDTO）。"""
    if rule_id is None:
        return None
    from sqlalchemy import text
    r = db.execute(text(
        "SELECT qid, cond, field, id, operator, type FROM queryrule WHERE qid = :q"
    ), {"q": rule_id}).fetchone()
    if not r:
        return None
    values = [v[0] for v in db.execute(text(
        "SELECT value FROM queryrule_values WHERE queryrule_id = :q ORDER BY value_order"
    ), {"q": rule_id}).fetchall()]
    children = db.execute(text(
        "SELECT qid FROM queryrule WHERE parent_query_rule = :q ORDER BY qid"
    ), {"q": rule_id}).fetchall()
    return {
        "condition": r[1],
        "field": r[2],
        "id": r[3],
        "operator": r[4],
        "type": r[5],
        "values": values,
        "rules": [_load_query_rule(db, c[0]) for c in children],
    }


def _load_query_contexts(db, query_id):
    from sqlalchemy import text
    rows = db.execute(text(
        "SELECT configurationitemid, serialnumber, workspaceid FROM querycontext "
        "WHERE query_id = :q"
    ), {"q": query_id}).fetchall()
    return [
        {"configurationItemId": r[0], "serialNumber": r[1], "workspaceId": r[2]}
        for r in rows
    ]


def _query_admin_flag(db, workspace_id, login):
    """判断用户对该工作区是否为管理员（工作区 admin 或全局 admin 组）。"""
    from sqlalchemy import text
    if workspace_id:
        ws_admin = db.execute(text(
            "SELECT 1 FROM workspace WHERE id=:w AND admin_login=:l"
        ), {"w": workspace_id, "l": login}).first()
        if ws_admin:
            return True
    return db.execute(text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": login}).first() is not None


def _run_custom_query(db, workspace_id, body, request, login):
    """运行自定义查询（对齐 Java runCustomQuery）：执行 + 可选保存 + 按 selects 序列化。"""
    from fastapi.responses import JSONResponse
    from app.services.query_executor import run_part_query
    from app.services.query_pbs import filter_pbs, merge_rows
    from app.schemas.query_result import build_query_result_rows

    export = (request.query_params.get("export") or "JSON").upper()
    save = str(request.query_params.get("save", "")).lower() in ("true", "1", "yes")
    if export == "CSV":
        return JSONResponse(status_code=400,
                            content={"message": "CSV export not supported"})
    is_admin = _query_admin_flag(db, workspace_id, login)
    parts = run_part_query(db, workspace_id, body, login, is_admin)
    if body.get("contexts"):
        pbs_rows = filter_pbs(db, workspace_id, body, login, is_admin)
        rows = merge_rows(pbs_rows, parts)
    else:
        rows = [{"partRevision": pr} for pr in parts]
    if save and body.get("name"):
        _save_query(db, workspace_id, login, body)
        db.commit()
    return build_query_result_rows(rows, body, db)


@router.post("/workspaces/{workspace_id}/parts/queries", response_model=list)
@router.post("/workspaces/{workspace_id}/parts/queries/", response_model=list, include_in_schema=False)
def post_workspace_query(workspace_id: str,
                         request: Request,
                         body: dict = Body(...),
                         current_user: Account = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    """运行/保存自定义查询（对齐 Java runCustomQuery，返回 QueryResult 行数组）。"""
    return _run_custom_query(db, workspace_id, body, request, current_user.login)


@router.post("/parts/queries")
@router.post("/parts/queries/", include_in_schema=False)
def post_queries(request: Request,
                 body: dict = Body(...),
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """无 workspace 前缀版本：从 body.contexts 推断工作区，无法推断则退回重名检查。"""
    ctxs = body.get("contexts") or []
    ws = ctxs[0].get("workspaceId") if ctxs else None
    if not ws:
        return {"id": 0}
    return _run_custom_query(db, ws, body, request, current_user.login)


@router.delete("/parts/queries/{query_id}", status_code=204)
@router.delete("/parts/queries/{query_id}/", status_code=204, include_in_schema=False)
def delete_query(query_id: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """删除已保存的查询及其关联记录（对齐 Java deleteQuery）。"""
    try:
        qid = int(query_id)
    except (TypeError, ValueError):
        return Response(status_code=204)
    _delete_query_by_id(db, qid)
    db.commit()
    return Response(status_code=204)


def _delete_query_by_id(db, query_id):
    """按 id 删除查询及其所有子表 + queryrule 树（供 _save_query 复用）。"""
    from sqlalchemy import text
    q = db.execute(text(
        "SELECT queryrule_id, pathdata_queryrule_id FROM query WHERE id = :q"
    ), {"q": query_id}).fetchone()
    if not q:
        return
    for tbl in ("query_selects", "query_order_by", "query_grouped_by", "querycontext"):
        db.execute(text(f"DELETE FROM {tbl} WHERE query_id = :q"), {"q": query_id})
    db.execute(text("DELETE FROM query WHERE id = :q"), {"q": query_id})
    for root_rule in (q[0], q[1]):
        _delete_query_rule(db, root_rule)


def _delete_query_rule(db, rule_id):
    """递归删除 queryrule 及其子规则、values。"""
    if rule_id is None:
        return
    from sqlalchemy import text
    children = db.execute(text(
        "SELECT qid FROM queryrule WHERE parent_query_rule = :q"
    ), {"q": rule_id}).fetchall()
    for c in children:
        _delete_query_rule(db, c[0])
    db.execute(text("DELETE FROM queryrule_values WHERE queryrule_id = :q"), {"q": rule_id})
    db.execute(text("DELETE FROM queryrule WHERE qid = :q"), {"q": rule_id})


def _save_query_rule(db, rule):
    """递归写入 queryrule 树，返回根 qid（对齐 Java QueryDAO.persistQueryRules）。"""
    if rule is None:
        return None
    from sqlalchemy import text
    qid = db.execute(text("SELECT nextval('queryrule_qid_seq')")).scalar()
    db.execute(text(
        "INSERT INTO queryrule (qid, cond, field, id, operator, type, parent_query_rule) "
        "VALUES (:qid, :cond, :field, :rid, :op, :type, NULL)"
    ), {"qid": qid, "cond": rule.get("condition"), "field": rule.get("field"),
        "rid": rule.get("id"), "op": rule.get("operator"), "type": rule.get("type")})
    for i, v in enumerate(rule.get("values") or []):
        db.execute(text(
            "INSERT INTO queryrule_values (queryrule_id, value, value_order) "
            "VALUES (:q, :v, :o)"
        ), {"q": qid, "v": str(v), "o": i})
    for child in rule.get("rules") or []:
        child_qid = _save_query_rule(db, child)
        db.execute(text("UPDATE queryrule SET parent_query_rule=:p WHERE qid=:c"),
                   {"p": qid, "c": child_qid})
    return qid


def _save_query(db, workspace_id, author_login, body):
    """保存自定义查询（对齐 Java ProductManagerBean.createQuery）。同名先删除。"""
    from sqlalchemy import text
    name = body.get("name")
    existing = db.execute(text(
        "SELECT id FROM query WHERE name=:n AND author_workspace_id=:w"
    ), {"n": name, "w": workspace_id}).fetchall()
    for e in existing:
        _delete_query_by_id(db, e[0])
    rule_id = _save_query_rule(db, body.get("queryRule"))
    pd_rule_id = _save_query_rule(db, body.get("pathDataQueryRule"))
    qid = db.execute(text("SELECT nextval('query_id_seq')")).scalar()
    db.execute(text(
        "INSERT INTO query (id, name, creationdate, author_workspace_id, author_login, "
        "queryrule_id, pathdata_queryrule_id) "
        "VALUES (:id, :n, now(), :w, :a, :r, :pr)"
    ), {"id": qid, "n": name, "w": workspace_id, "a": author_login,
        "r": rule_id, "pr": pd_rule_id})
    for s in body.get("selects") or []:
        db.execute(text("INSERT INTO query_selects (query_id, selects) VALUES (:q,:s)"),
                   {"q": qid, "s": s})
    for o in body.get("orderByList") or []:
        db.execute(text("INSERT INTO query_order_by (query_id, orderbylist) VALUES (:q,:o)"),
                   {"q": qid, "o": o})
    for g in body.get("groupedByList") or []:
        db.execute(text("INSERT INTO query_grouped_by (query_id, groupedbylist) VALUES (:q,:g)"),
                   {"q": qid, "g": g})
    for c in body.get("contexts") or []:
        cid = db.execute(text("SELECT nextval('querycontext_id_seq')")).scalar()
        db.execute(text(
            "INSERT INTO querycontext (id, configurationitemid, serialnumber, workspaceid, query_id) "
            "VALUES (:id, :ci, :sn, :ws, :q)"
        ), {"id": cid, "ci": c.get("configurationItemId"), "sn": c.get("serialNumber"),
            "ws": c.get("workspaceId") or workspace_id, "q": qid})
    return qid


@router.get("/parts/query-export",
            response_model=dict)
@router.get("/parts/query-export/",
            response_model=dict, include_in_schema=False)
def query_export(request: Request,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """导出零件查询结果为 JSON 或 CSV（exportType=json|xls）。

    对齐 Java QueryResultMessageBodyWriter。
    """
    from app.routers.export.query_result import export_query_as_json, export_query_as_csv
    from fastapi.responses import Response

    params = dict(request.query_params)
    export_type = params.get("exportType", "json")

    if export_type == "xls":
        csv_data = export_query_as_csv(db, "", params)
        return Response(
            content=csv_data,
            media_type="application/csv",
            headers={"Content-Disposition": 'attachment; filename="TSR.csv"'},
        )
    else:
        json_data = export_query_as_json(db, "", params)
        return Response(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": "inline"},
        )


# ── imports ────────────────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/parts/imports/{filename}",
            response_model=list[ImportDTO])
@router.get("/workspaces/{workspace_id}/parts/imports/{filename}/",
            response_model=list[ImportDTO], include_in_schema=False)
def imports_get(workspace_id: str, filename: str,
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """列出某 workspace 下指定 filename 的所有导入记录。"""
    return list_imports(db, user_workspace_id=workspace_id, filename=filename)


@router.get("/workspaces/{workspace_id}/parts/import/{import_id}",
            response_model=ImportDTO)
@router.get("/workspaces/{workspace_id}/parts/import/{import_id}/",
            response_model=ImportDTO, include_in_schema=False)
def import_get(workspace_id: str, import_id: str,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    """按 id 读取单条导入记录。不存在返回 404。"""
    dto = get_import(db, import_id)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Import {import_id} not found")
    return dto


@router.post("/workspaces/{workspace_id}/parts/import",
             status_code=204)
@router.post("/workspaces/{workspace_id}/parts/import/",
             status_code=204, include_in_schema=False)
def post_import(workspace_id: str,
                upload: UploadFile = File(...),
                autoCheckout: bool = Query(False),
                autoCheckin: bool = Query(False),
                permissiveUpdate: bool = Query(False),
                revisionNote: str = Query(""),
                importType: str = Query(...),
                current_user: Account = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """批量导入 excel 属性/BOM 数据。返回 204，通过 GET imports/{filename} 轮询结果。"""
    if importType not in ("attributes", "bom"):
        raise HTTPException(status_code=400, detail=f"Invalid importType: {importType}")

    data = upload.file.read()
    filename = upload.filename
    import_id = uuid.uuid4().hex
    file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            file_path = tmp.name
            tmp.write(data)

        # 先算权限，避免 _query_admin_flag 抛错时留下 pending 孤儿导入记录
        is_admin = _query_admin_flag(db, workspace_id, current_user.login)
        create_import(db, import_id, filename, current_user.login, workspace_id)

        try:
            if importType == "attributes":
                result = importer_service.import_into_parts(
                    db, workspace_id, file_path, filename,
                    user_login=current_user.login, is_admin=is_admin,
                    revision_note=revisionNote,
                    auto_checkout=autoCheckout,
                    auto_checkin=autoCheckin,
                    permissive_update=permissiveUpdate,
                )
            else:
                result = importer_service.import_bom(
                    db, workspace_id, file_path, filename,
                    user_login=current_user.login, is_admin=is_admin,
                    revision_note=revisionNote,
                    auto_checkout=autoCheckout,
                    auto_checkin=autoCheckin,
                    permissive_update=permissiveUpdate,
                )
            complete_import(db, import_id,
                            result.get("succeed", False),
                            result.get("errors", []),
                            result.get("warnings", []))
        except Exception as e:
            complete_import(db, import_id, False, [str(e)], [])
    finally:
        if file_path:
            try:
                os.unlink(file_path)
            except OSError:
                pass

    return Response(status_code=204)


@router.post("/workspaces/{workspace_id}/parts/importPreview",
             response_model=ImportPreviewDTO)
@router.post("/workspaces/{workspace_id}/parts/importPreview/",
             response_model=ImportPreviewDTO, include_in_schema=False)
def post_import_preview(workspace_id: str,
                        upload: UploadFile = File(...),
                        autoCheckout: bool = Query(False),
                        autoCheckin: bool = Query(False),
                        permissiveUpdate: bool = Query(False),
                        importType: str = Query(...),
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """试运行导入——返回需要 checkout 的零件列表（不写库）。"""
    if importType not in ("attributes", "bom"):
        raise HTTPException(status_code=400, detail=f"Invalid importType: {importType}")

    data = upload.file.read()
    filename = upload.filename
    file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            file_path = tmp.name
            tmp.write(data)

        is_admin = _query_admin_flag(db, workspace_id, current_user.login)

        if importType == "attributes":
            result = importer_service.dry_run_import_into_parts(
                db, workspace_id, file_path, filename,
                user_login=current_user.login, is_admin=is_admin,
                auto_checkout=autoCheckout,
                auto_checkin=autoCheckin,
                permissive_update=permissiveUpdate,
            )
        else:
            result = importer_service.dry_run_import_bom(
                db, workspace_id, file_path, filename,
                user_login=current_user.login, is_admin=is_admin,
                auto_checkout=autoCheckout,
                auto_checkin=autoCheckin,
                permissive_update=permissiveUpdate,
            )

        return ImportPreviewDTO(
            partRevsToCheckout=result.get("partRevsToCheckout", []),
            partsToCreate=result.get("partsToCreate", []),
        )
    finally:
        if file_path:
            try:
                os.unlink(file_path)
            except OSError:
                pass


@router.delete("/workspaces/{workspace_id}/parts/import/{import_id}",
               status_code=204)
@router.delete("/workspaces/{workspace_id}/parts/import/{import_id}/",
               status_code=204, include_in_schema=False)
def delete_import(workspace_id: str, import_id: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """删除导入记录及其子表。"""
    delete_import_record(db, import_id)
    return Response(status_code=204)
