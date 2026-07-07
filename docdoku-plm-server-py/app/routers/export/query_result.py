"""查询结果导出工具（实施 QueryResultMessageBodyWriter 的核心逻辑）。

此模块不注册路由，导出函数供 parts.py 中的 query-export stub 调用。
"""
import csv
import io
import json
import logging
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.services.file_export.search_query_parser import parse_part_query

_logger = logging.getLogger(__name__)


def _json_serializer(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def export_query_as_json(db: Session, workspace_id: str, query_params: dict) -> str:
    """导出零件查询结果为 JSON 字符串。

    对齐 Java QueryResultMessageBodyWriter.generateJSONResponse()。
    """
    parsed = parse_part_query(workspace_id, query_params)

    from app.models.part import PartRevision, PartMaster
    q = db.query(PartRevision, PartMaster).join(
        PartMaster,
        (PartRevision.workspace_id == PartMaster.workspace_id)
        & (PartRevision.partmaster_partnumber == PartMaster.number),
    ).filter(PartRevision.workspace_id == workspace_id)

    if parsed.get("q"):
        like = f"%{parsed['q']}%"
        from sqlalchemy import or_
        q = q.filter(or_(
            PartMaster.number.ilike(like),
            PartMaster.name.ilike(like),
            PartRevision.description.ilike(like),
        ))
    if parsed.get("version"):
        q = q.filter(PartRevision.version == parsed["version"])
    if parsed.get("author"):
        q = q.filter(PartRevision.author_login == parsed["author"])
    if parsed.get("tags"):
        from app.models.part import part_revision_tags
        q = q.join(part_revision_tags).filter(
            part_revision_tags.c.tag_label.in_(parsed["tags"])
        ).distinct()

    rows = q.limit(1000).all()

    status_map = {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}
    result = []
    for rev, master in rows:
        result.append({
            "number": master.number,
            "name": master.name or "",
            "version": rev.version,
            "description": rev.description or "",
            "status": status_map.get(rev.status, "WIP"),
            "author": rev.author_login or "",
            "creationDate": rev.creation_date.isoformat() if rev.creation_date else None,
            "standardPart": master.standard_part,
            "type": master.part_type,
        })

    return json.dumps(result, default=_json_serializer, ensure_ascii=False)


def export_query_as_csv(db: Session, workspace_id: str, query_params: dict) -> str:
    """导出零件查询结果为 CSV 字符串。"""
    parsed = parse_part_query(workspace_id, query_params)

    from app.models.part import PartRevision, PartMaster
    q = db.query(PartRevision, PartMaster).join(
        PartMaster,
        (PartRevision.workspace_id == PartMaster.workspace_id)
        & (PartRevision.partmaster_partnumber == PartMaster.number),
    ).filter(PartRevision.workspace_id == workspace_id)

    if parsed.get("q"):
        like = f"%{parsed['q']}%"
        from sqlalchemy import or_
        q = q.filter(or_(
            PartMaster.number.ilike(like),
            PartMaster.name.ilike(like),
            PartRevision.description.ilike(like),
        ))
    if parsed.get("version"):
        q = q.filter(PartRevision.version == parsed["version"])
    if parsed.get("author"):
        q = q.filter(PartRevision.author_login == parsed["author"])
    if parsed.get("tags"):
        from app.models.part import part_revision_tags
        q = q.join(part_revision_tags).filter(
            part_revision_tags.c.tag_label.in_(parsed["tags"])
        ).distinct()

    rows = q.limit(1000).all()

    status_map = {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["number", "name", "version", "description", "status", "author", "creationDate"])
    for rev, master in rows:
        writer.writerow([
            master.number,
            master.name or "",
            rev.version,
            rev.description or "",
            status_map.get(rev.status, "WIP"),
            rev.author_login or "",
            rev.creation_date.isoformat() if rev.creation_date else "",
        ])
    return output.getvalue()
