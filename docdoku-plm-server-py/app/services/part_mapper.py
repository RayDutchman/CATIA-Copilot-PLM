"""PartRevision/PartIteration/PartUsageLink → DTO 映射工具。"""
from datetime import timezone
from sqlalchemy.orm import Session
from app.models.part import PartRevision, PartIteration, PartUsageLink, BinaryResource
from app.models.auth import Account
from app.schemas.part import (
    PartRevisionDTO, PartIterationDTO, PartUsageLinkDTO,
    ComponentDTO, CADInstanceDTO, BinaryResourceDTO, UserDTO,
)

STATUS_MAP = {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}


def _user_dto(workspace_id, login, db: Session | None = None) -> UserDTO | None:
    """构造 UserDTO，从 Account 表补全 name/email/language。"""
    if not login:
        return None
    name = email = language = None
    if db is not None:
        acct = db.query(Account).filter(Account.login == login).first()
        if acct:
            name = acct.name
            email = acct.email
            language = acct.language
    return UserDTO(
        login=login,
        workspaceId=workspace_id,
        name=name,
        email=email,
        language=language,
    )


def _to_utc(dt):
    """确保 datetime 以 UTC 序列化（与 Payara 的 .178Z 格式对齐）。"""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _binary_dto(br: BinaryResource | None) -> BinaryResourceDTO | None:
    if br is None:
        return None
    name = br.full_name.split("/")[-1] if br.full_name else ""
    return BinaryResourceDTO(
        fullName=br.full_name,
        name=name,
        contentLength=br.content_length,
        lastModified=br.last_modified,
    )


def _build_acl(db: Session | None, acl_id: int | None) -> dict | None:
    if db is None or acl_id is None:
        return None
    from app.models.security import ACL, AclUserEntry, AclUserGroupEntry
    acl = db.query(ACL).filter(ACL.id == acl_id).first()
    if not acl:
        return None
    user_entries = db.query(AclUserEntry).filter(AclUserEntry.acl_id == acl_id).all()
    group_entries = db.query(AclUserGroupEntry).filter(AclUserGroupEntry.acl_id == acl_id).all()
    _PERM = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}
    return {
        "userEntries": [{"key": e.principal_login, "value": _PERM.get(e.permission, "FORBIDDEN")} for e in user_entries],
        "groupEntries": [{"key": e.principal_id, "value": _PERM.get(e.permission, "FORBIDDEN")} for e in group_entries],
        "userEntriesMap": {e.principal_login: _PERM.get(e.permission, "FORBIDDEN") for e in user_entries},
        "userGroupEntriesMap": {},
    }


def map_cad_instance(cad) -> CADInstanceDTO:
    return CADInstanceDTO(
        rotationType=cad.rotation_type,
        rx=cad.rx, ry=cad.ry, rz=cad.rz,
        tx=cad.tx, ty=cad.ty, tz=cad.tz,
        m00=cad.m00, m01=cad.m01, m02=cad.m02,
        m10=cad.m10, m11=cad.m11, m12=cad.m12,
        m20=cad.m20, m21=cad.m21, m22=cad.m22,
    )


def map_usage_link(link: PartUsageLink) -> PartUsageLinkDTO:
    comp_dto = None
    if link.component:
        comp_dto = ComponentDTO(
            number=link.component.number,
            name=link.component.name or "",
            standardPart=link.component.standard_part or False,
        )
    return PartUsageLinkDTO(
        id=link.id,
        amount=link.amount if link.amount is not None else 1.0,
        comment=link.comment,
        referenceDescription=link.reference_description,
        unit=link.unit,
        optional=link.optional or False,
        component=comp_dto,
        cadInstances=[map_cad_instance(c) for c in (link.cad_instances or [])],
    )


def map_iteration(it: PartIteration, db: Session | None = None) -> PartIterationDTO:
    # geometryFileURI：逗号分隔所有 GLB 几何体的 URI
    geometries = it.geometries or []
    geometry_uri = ",".join(
        [f"/api/files/{g.full_name}" for g in geometries]
    ) if geometries else None

    # instanceAttributes：从 partiteration_attribute + instanceattribute 查询
    instance_attributes = []
    if db is not None:
        from sqlalchemy import text
        attr_rows = db.execute(text(
            "SELECT ia.name, ia.mandatory, ia.locked, "
            "ia.booleanvalue, ia.datevalue, ia.indexvalue, "
            "ia.numbervalue, ia.textvalue, ia.longtextvalue, ia.urlvalue "
            "FROM partiteration_attribute pia "
            "JOIN instanceattribute ia ON ia.id = pia.instanceattribute_id "
            "WHERE pia.workspace_id=:ws AND pia.partmaster_partnumber=:pn "
            "AND pia.partrevision_version=:ver AND pia.iteration=:it "
            "ORDER BY pia.attribute_order"
        ), {"ws": it.workspace_id, "pn": it.partmaster_partnumber,
            "ver": it.partrevision_version, "it": it.iteration}).fetchall()
        instance_attributes = [dict(row._mapping) for row in attr_rows]

    # linkedDocuments：从 partiteration_documentlink + documentlink 查询
    linked_documents = []
    if db is not None:
        from sqlalchemy import text
        doc_rows = db.execute(text(
            "SELECT dl.id, dl.target_workspace_id, dl.target_documentmaster_id, "
            "dl.target_docrevision_version, dl.commentdata "
            "FROM partiteration_documentlink pidl "
            "JOIN documentlink dl ON dl.id = pidl.documentlink_id "
            "WHERE pidl.workspace_id=:ws AND pidl.partmaster_partnumber=:pn "
            "AND pidl.partrevision_version=:ver AND pidl.iteration=:it"
        ), {"ws": it.workspace_id, "pn": it.partmaster_partnumber,
            "ver": it.partrevision_version, "it": it.iteration}).fetchall()
        linked_documents = [dict(row._mapping) for row in doc_rows]

    return PartIterationDTO(
        workspaceId=it.workspace_id,
        number=it.partmaster_partnumber,
        version=it.partrevision_version,
        iteration=it.iteration,
        iterationNote=it.iteration_note,
        author=_user_dto(it.author_workspace_id, it.author_login, db),
        creationDate=_to_utc(it.creation_date),
        modificationDate=_to_utc(it.modification_date),
        checkInDate=_to_utc(it.check_in_date),
        nativeCADFile=_binary_dto(it.native_cad_file),
        geometryFileURI=geometry_uri,
        instanceAttributes=instance_attributes,
        instanceAttributeTemplates=[],
        linkedDocuments=linked_documents,
        attachedFiles=[_binary_dto(f) for f in (it.attached_files or []) if f],
        components=[map_usage_link(l) for l in (it.components or [])],
    )


def map_revision(pr: PartRevision, db: Session | None = None) -> PartRevisionDTO:
    master = pr.part_master
    iterations = sorted(pr.iterations or [], key=lambda x: x.iteration)
    last_it = iterations[-1] if iterations else None

    workspace_id = pr.workspace_id
    number = pr.partmaster_partnumber
    version = pr.version
    notification_list = []
    if db is not None:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT mn.id, mn.acknowledged, mn.acknowledgementcomment, mn.acknowledgementdate, "
            "mn.ackauthor_login, mn.ackauthor_workspace_id, "
            "mn.impacted_partrevision_version, mn.impacted_iteration, "
            "mn.impacted_workspace_id, mn.impacted_partmaster_partnumber, "
            "mn.modified_workspace_id, mn.modified_partmaster_partnumber, "
            "mn.modified_iteration, mn.modified_partrevision_version, "
            "pm.name AS modified_part_name, "
            "pi.iterationnote AS modified_iteration_note, "
            "pi.checkindate AS modified_check_in_date, "
            "pi.author_login AS modified_author_login, "
            "pi.author_workspace_id AS modified_author_workspace_id "
            "FROM modificationnotification mn "
            "LEFT JOIN partmaster pm ON pm.partnumber = mn.modified_partmaster_partnumber "
            "  AND pm.workspace_id = mn.modified_workspace_id "
            "LEFT JOIN partiteration pi ON pi.partmaster_partnumber = mn.modified_partmaster_partnumber "
            "  AND pi.partrevision_version = mn.modified_partrevision_version "
            "  AND pi.workspace_id = mn.modified_workspace_id "
            "  AND pi.iteration = mn.modified_iteration "
            "WHERE mn.impacted_workspace_id = :ws "
            "  AND mn.impacted_partmaster_partnumber = :pn "
            "  AND mn.impacted_partrevision_version = :ver "
            "ORDER BY mn.id"
        ), {"ws": workspace_id, "pn": number, "ver": version}).fetchall()
        for row in rows:
            row_d = dict(row._mapping)
            author_dto = _user_dto(
                row_d.get("modified_author_workspace_id"),
                row_d.get("modified_author_login"), db,
            )
            ack_author_dto = None
            if row_d.get("ackauthor_login"):
                ack_author_dto = _user_dto(
                    row_d.get("ackauthor_workspace_id"),
                    row_d.get("ackauthor_login"), db,
                )
            notification_list.append({
                "id": row_d["id"],
                "impactedPartNumber": row_d["impacted_partmaster_partnumber"],
                "impactedPartVersion": row_d["impacted_partrevision_version"],
                "modifiedPartNumber": row_d["modified_partmaster_partnumber"],
                "modifiedPartName": row_d.get("modified_part_name") or "",
                "modifiedPartVersion": row_d["modified_partrevision_version"],
                "modifiedPartIteration": row_d["modified_iteration"],
                "checkInDate": _to_utc(row_d.get("modified_check_in_date")),
                "iterationNote": row_d.get("modified_iteration_note") or "",
                "author": author_dto.model_dump() if author_dto else {},
                "acknowledged": row_d.get("acknowledged", False) or False,
                "ackComment": row_d.get("acknowledgementcomment") or "",
                "ackAuthor": ack_author_dto.model_dump() if ack_author_dto else {},
                "ackDate": _to_utc(row_d.get("acknowledgementdate")),
            })

    return PartRevisionDTO(
        workspaceId=pr.workspace_id,
        number=pr.partmaster_partnumber,
        version=pr.version,
        partKey=f"{pr.partmaster_partnumber}-{pr.version}",
        name=master.name if master else "",
        type=master.type if master else None,
        standardPart=(master.standard_part or False) if master else False,
        attributesLocked=(master.attributes_locked or False) if master else False,
        author=_user_dto(pr.author_workspace_id, pr.author_login, db),
        creationDate=_to_utc(pr.creation_date),
        modificationDate=_to_utc(last_it.modification_date) if last_it else None,
        checkInDate=_to_utc(last_it.check_in_date) if last_it else None,
        description=pr.description or "",
        lastIterationNumber=last_it.iteration if last_it else 0,
        partIterations=[map_iteration(it, db) for it in iterations],
        checkOutUser=_user_dto(pr.checkout_user_workspace_id, pr.checkout_user_login, db),
        checkOutDate=_to_utc(pr.check_out_date),
        status=STATUS_MAP.get(pr.status, "WIP"),
        publicShared=pr.public_shared or False,
        releaseDate=_to_utc(pr.release_date),
        releaseAuthor=_user_dto(pr.release_user_workspace, pr.release_user_login, db),
        obsoleteDate=_to_utc(pr.obsolete_date),
        obsoleteAuthor=_user_dto(pr.obsolete_user_workspace, pr.obsolete_user_login, db),
        tags=[t.label for t in (pr.tags or [])],
        workflow=None,
        acl=_build_acl(db, pr.acl_id) if db else None,
        notifications=notification_list,
    )
