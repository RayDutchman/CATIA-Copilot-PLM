"""转换回调处理，对齐 Payara handleConversionResultCallback（保留 race/空几何修复）。"""
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services import vault, binary_storage
from app.models.part import (
    Conversion, BinaryResource, PartUsageLink, CADInstance,
    part_iteration_geometry, usage_link_cadinstances,
)
from app.schemas.part import ConversionResultDTO, PositionDTO

logger = logging.getLogger(__name__)


def find_pending_conversion(db: Session, ws: str, pn: str,
                            ver: str) -> Conversion | None:
    """查该 revision 下 pending=True 的 Conversion，定位真正发起转换的 iteration。"""
    return db.query(Conversion).filter(
        Conversion.workspace_id == ws,
        Conversion.partmaster_partnumber == pn,
        Conversion.partrevision_version == ver,
        Conversion.pending.is_(True),
    ).first()


def end_conversion(db: Session, conv: Conversion, succeed: bool) -> None:
    conv.pending = False
    conv.succeed = succeed
    conv.end_date = datetime.utcnow()
    db.flush()


def _save_geometry_file(db: Session, ws: str, pn: str, ver: str,
                         iteration: int, quality: int, glb_name: str,
                         temp_dir: str, box: list[float]) -> None:
    """保存单个 LOD 几何体文件到 vault + BinaryResource + 关联。"""
    src = Path(settings.CONVERSIONS_PATH) / temp_dir / glb_name
    data = src.read_bytes()
    from app.services.vault import _vault_root
    dst = _vault_root() / ws / "parts" / pn / ver / str(iteration) / glb_name
    vault.write_file(dst, data)
    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/{glb_name}"
    bbox = box or [0, 0, 0, 0, 0, 0]
    br = db.query(BinaryResource).filter(
        BinaryResource.full_name == full_name).first()
    if br is None:
        br = BinaryResource(
            full_name=full_name, dtype="Geometry",
            content_length=len(data), last_modified=datetime.utcnow(),
            quality=quality,
            x_min=bbox[0], y_min=bbox[1], z_min=bbox[2],
            x_max=bbox[3], y_max=bbox[4], z_max=bbox[5],
        )
        db.add(br)
        db.flush()
    else:
        br.quality = quality
        br.content_length = len(data)
        br.last_modified = datetime.utcnow()
        db.flush()
    exists = db.execute(
        part_iteration_geometry.select().where(
            part_iteration_geometry.c.workspace_id == ws,
            part_iteration_geometry.c.partmaster_partnumber == pn,
            part_iteration_geometry.c.partrevision_version == ver,
            part_iteration_geometry.c.iteration == iteration,
            part_iteration_geometry.c.geometry_fullname == full_name,
        )
    ).first()
    if exists is None:
        db.execute(part_iteration_geometry.insert().values(
            workspace_id=ws, partmaster_partnumber=pn,
            partrevision_version=ver, iteration=iteration,
            geometry_fullname=full_name,
        ))


def _save_material_as_attached(db: Session, ws: str, pn: str, ver: str,
                                iteration: int, material_name: str,
                                temp_dir: str) -> None:
    """将材质文件保存为附件。"""
    src = Path(settings.CONVERSIONS_PATH) / temp_dir / material_name
    data = src.read_bytes()
    path = vault.part_attached_path(ws, pn, ver, iteration, material_name)
    vault.write_file(path, data)
    from app.models.part import part_iteration_binres
    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/attachedfiles/{material_name}"
    br = db.query(BinaryResource).filter(
        BinaryResource.full_name == full_name).first()
    if br is None:
        br = BinaryResource(
            full_name=full_name, dtype="BinaryResource",
            content_length=len(data), last_modified=datetime.utcnow(),
        )
        db.add(br)
        db.flush()
    else:
        br.content_length = len(data)
        br.last_modified = datetime.utcnow()
        db.flush()
    exists = db.execute(
        part_iteration_binres.select().where(
            part_iteration_binres.c.workspace_id == ws,
            part_iteration_binres.c.partmaster_partnumber == pn,
            part_iteration_binres.c.partrevision_version == ver,
            part_iteration_binres.c.iteration == iteration,
            part_iteration_binres.c.attachedfile_fullname == full_name,
        )
    ).first()
    if exists is None:
        db.execute(part_iteration_binres.insert().values(
            workspace_id=ws, partmaster_partnumber=pn,
            partrevision_version=ver, iteration=iteration,
            attachedfile_fullname=full_name,
        ))


def _to_cad_instance(pos: PositionDTO) -> CADInstance:
    """将 PositionDTO 转为 CADInstance 模型（矩阵模式）。"""
    rm = pos.rotationmatrix
    t = pos.translation or [0, 0, 0]
    if rm and len(rm) == 3 and len(rm[0]) == 3:
        return CADInstance(
            rotation_type="MATRIX",
            tx=t[0] if len(t) > 0 else 0,
            ty=t[1] if len(t) > 1 else 0,
            tz=t[2] if len(t) > 2 else 0,
            m00=rm[0][0], m01=rm[0][1], m02=rm[0][2],
            m10=rm[1][0], m11=rm[1][1], m12=rm[1][2],
            m20=rm[2][0], m21=rm[2][1], m22=rm[2][2],
        )
    return CADInstance(
        rotation_type="ANGLE",
        tx=t[0] if len(t) > 0 else 0,
        ty=t[1] if len(t) > 1 else 0,
        tz=t[2] if len(t) > 2 else 0,
    )


def sync_assembly(db: Session, ws: str, pn: str, ver: str, iteration: int,
                  component_position_map: dict[str, list[PositionDTO]]) -> bool:
    """同步装配结构：根据转换结果的 componentPositionMap 创建 PartUsageLink + CADInstance。
    对齐 Java ConverterBean.syncAssembly()。
    返回 True 表示成功（即使某些组件未找到也继续处理，仅 warn）。
    """
    from app.services.product_manager import ProductService
    svc = ProductService()
    succeed = True
    part_usage_links = []
    for cad_filename, positions in component_position_map.items():
        master = svc.find_part_master_by_cad_filename(db, ws, cad_filename)
        if master is None:
            logger.warning("No Part found for %s", cad_filename)
            succeed = False
            continue
        link = PartUsageLink(
            amount=len(positions),
            component_workspace_id=master.workspace_id,
            component_partnumber=master.number,
        )
        db.add(link)
        db.flush()
        for pos in positions:
            cad = _to_cad_instance(pos)
            db.add(cad)
            db.flush()
            db.execute(usage_link_cadinstances.insert().values(
                partusagelink_id=link.id,
                cadinstance_id=cad.id,
            ))
        part_usage_links.append(link)
    if part_usage_links:
        svc.update_usage_links_in_converted_iteration(
            db, ws, pn, ver, iteration, part_usage_links)
    if succeed:
        logger.info("Assembly synchronized: %s/%s-%s iter=%d", ws, pn, ver, iteration)
    return succeed


def handle_callback(db: Session, ws: str, pn: str, ver: str,
                    result: ConversionResultDTO) -> None:
    conv = find_pending_conversion(db, ws, pn, ver)
    if conv is None:
        return
    iteration = conv.iteration
    err = (result.errorOutput or "")
    if "no geometry generated" in err.lower():
        end_conversion(db, conv, True)
        return
    if err:
        end_conversion(db, conv, False)
        return

    component_position_map = result.componentPositionMap
    converted_file_lods = result.convertedFileLODs or {}

    if not converted_file_lods and not component_position_map:
        end_conversion(db, conv, False)
        return

    # Fix 1: 同步装配结构 (componentPositionMap)
    if component_position_map:
        if not sync_assembly(db, ws, pn, ver, iteration, component_position_map):
            # 即使部分组件未匹配，仍然继续保存几何体
            logger.warning(
                "Assembly sync partially failed for %s/%s-%s iter=%d",
                ws, pn, ver, iteration)

    # Fix 4: 保存材质文件为附件
    materials = result.materials or []
    if materials:
        logger.info("Saving materials: %d files", len(materials))
        for material_name in materials:
            _save_material_as_attached(
                db, ws, pn, ver, iteration, material_name, result.tempDir)

    # Fix 3: 多 LOD 支持（遍历所有 quality level）
    box = result.box or [0, 0, 0, 0, 0, 0]
    for quality_str, glb_name in converted_file_lods.items():
        try:
            quality = int(quality_str)
        except (ValueError, TypeError):
            quality = 0
        _save_geometry_file(db, ws, pn, ver, iteration, quality,
                            glb_name, result.tempDir, box)

    end_conversion(db, conv, True)
