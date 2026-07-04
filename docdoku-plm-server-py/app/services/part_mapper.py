"""PartRevision/PartIteration/PartUsageLink → DTO 映射工具。"""
from app.models.part import PartRevision, PartIteration, PartUsageLink, BinaryResource
from app.schemas.part import (
    PartRevisionDTO, PartIterationDTO, PartUsageLinkDTO,
    ComponentDTO, CADInstanceDTO, BinaryResourceDTO, UserDTO,
)

STATUS_MAP = {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}


def _user_dto(workspace_id, login) -> UserDTO | None:
    if not login:
        return None
    return UserDTO(login=login, workspaceId=workspace_id)


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


def map_iteration(it: PartIteration) -> PartIterationDTO:
    return PartIterationDTO(
        workspaceId=it.workspace_id,
        number=it.partmaster_partnumber,
        version=it.partrevision_version,
        iteration=it.iteration,
        iterationNote=it.iteration_note,
        author=_user_dto(it.author_workspace_id, it.author_login),
        creationDate=it.creation_date,
        modificationDate=it.modification_date,
        checkInDate=it.check_in_date,
        nativeCADFile=_binary_dto(it.native_cad_file),
        attachedFiles=[_binary_dto(f) for f in (it.attached_files or []) if f],
        components=[map_usage_link(l) for l in (it.components or [])],
    )


def map_revision(pr: PartRevision) -> PartRevisionDTO:
    master = pr.part_master
    iterations = sorted(pr.iterations or [], key=lambda x: x.iteration)
    last_it = iterations[-1] if iterations else None
    return PartRevisionDTO(
        workspaceId=pr.workspace_id,
        number=pr.partmaster_partnumber,
        version=pr.version,
        partKey=f"{pr.partmaster_partnumber}-{pr.version}",
        name=master.name if master else "",
        type=master.type if master else None,
        standardPart=(master.standard_part or False) if master else False,
        attributesLocked=(master.attributes_locked or False) if master else False,
        author=_user_dto(pr.author_workspace_id, pr.author_login),
        creationDate=pr.creation_date,
        checkInDate=last_it.check_in_date if last_it else None,
        description=pr.description or "",
        lastIterationNumber=last_it.iteration if last_it else 0,
        partIterations=[map_iteration(it) for it in iterations],
        checkOutUser=_user_dto(pr.checkout_user_workspace_id, pr.checkout_user_login),
        checkOutDate=pr.check_out_date,
        status=STATUS_MAP.get(pr.status, "WIP"),
        publicShared=pr.public_shared or False,
        releaseDate=pr.release_date,
        releaseAuthor=_user_dto(pr.release_user_workspace, pr.release_user_login),
        obsoleteDate=pr.obsolete_date,
        obsoleteAuthor=_user_dto(pr.obsolete_user_workspace, pr.obsolete_user_login),
        tags=[t.label for t in (pr.tags or [])],
    )
