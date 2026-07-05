"""转换回调服务测试。"""
import os
import uuid
import shutil
from pathlib import Path
from app.services import conversion_service
from app.services.product_service import ProductService
from app.schemas.part import ConversionResultDTO, PositionDTO
from app.models.part import (
    BinaryResource, part_iteration_geometry, part_iteration_binres,
    Conversion, PartIteration, PartRevision, PartMaster,
    PartUsageLink, CADInstance, usage_link_cadinstances,
)
from app.core.config import settings
from app.services import vault

WS = "Workspace_2"
svc = ProductService()


def _make_part_with_conversion(db, num):
    from app.schemas.part import PartCreationDTO
    # 预清理（避免上一次运行中断的残留数据）
    for n in [num]:
        db.query(Conversion).filter(
            Conversion.workspace_id == WS,
            Conversion.partmaster_partnumber == n,
        ).delete()
        db.execute(part_iteration_geometry.delete().where(
            part_iteration_geometry.c.workspace_id == WS,
            part_iteration_geometry.c.partmaster_partnumber == n,
        ))
        db.query(BinaryResource).filter(
            BinaryResource.full_name.like(f'{WS}/parts/{n}%'),
        ).delete()
        db.query(PartIteration).filter(
            PartIteration.workspace_id == WS,
            PartIteration.partmaster_partnumber == n,
        ).delete()
        db.query(PartRevision).filter(
            PartRevision.workspace_id == WS,
            PartRevision.partmaster_partnumber == n,
        ).delete()
        db.query(PartMaster).filter(
            PartMaster.workspace_id == WS,
            PartMaster.number == n,
        ).delete()
    db.commit()
    svc.create_part(db, WS, "test1", PartCreationDTO(number=num, name="t"))
    svc.create_conversion(db, WS, num, "A", 1)
    db.commit()


def test_callback_no_geometry_marks_succeed(db):
    num = "P1BCV-EMPTY-1"
    _make_part_with_conversion(db, num)
    conversion_service.handle_callback(db, WS, num, "A",
        ConversionResultDTO(errorOutput="no geometry generated"))
    db.commit()
    conv = svc.get_conversion(db, WS, num, "A", 1)
    assert conv.pending is False
    assert conv.succeed is True
    # 删除 conversion 记录再清理
    db.delete(conv)
    db.commit()
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")


def test_callback_error_marks_failed(db):
    num = "P1BCV-ERR-1"
    _make_part_with_conversion(db, num)
    conversion_service.handle_callback(db, WS, num, "A",
        ConversionResultDTO(errorOutput="some real error"))
    db.commit()
    conv = svc.get_conversion(db, WS, num, "A", 1)
    assert conv.pending is False
    assert conv.succeed is False
    db.delete(conv)
    db.commit()
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")


def test_callback_success_writes_glb(db):
    num = "P1BCV-OK-1"
    _make_part_with_conversion(db, num)
    temp_dir = str(uuid.uuid4())
    glb_name = f"{uuid.uuid4()}.glb"
    conv_dir = Path(settings.CONVERSIONS_PATH) / temp_dir
    conv_dir.mkdir(parents=True, exist_ok=True)
    (conv_dir / glb_name).write_bytes(b"GLBDATA")
    conversion_service.handle_callback(db, WS, num, "A",
        ConversionResultDTO(tempDir=temp_dir,
                            convertedFileLODs={"0": glb_name},
                            box=[-1, -1, -1, 1, 1, 1]))
    db.commit()
    conv = svc.get_conversion(db, WS, num, "A", 1)
    assert conv.succeed is True
    fn = f"{WS}/parts/{num}/A/1/{glb_name}"
    br = db.query(BinaryResource).filter(BinaryResource.full_name == fn).first()
    assert br is not None and br.dtype == "Geometry"
    assert br.x_min == -1 and br.z_max == 1
    glb_path = Path(settings.VAULT_PATH) / WS / "parts" / num / "A" / "1" / glb_name
    assert glb_path.read_bytes() == b"GLBDATA"
    # 清理：先删关联表，再删 BinaryResource，再删 conversion
    db.execute(part_iteration_geometry.delete().where(
        part_iteration_geometry.c.workspace_id == WS,
        part_iteration_geometry.c.partmaster_partnumber == num,
        part_iteration_geometry.c.partrevision_version == "A",
        part_iteration_geometry.c.iteration == 1,
    ))
    if br:
        db.delete(br)
    db.delete(conv)
    db.commit()
    os.remove(glb_path)
    shutil.rmtree(conv_dir, ignore_errors=True)
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")


def test_callback_multi_lod_saves_all(db):
    """Fix 3: 多 LOD 都保存，且 quality 正确写入 BinaryResource。"""
    num = "P1BCV-MLOD-1"
    _make_part_with_conversion(db, num)
    temp_dir = str(uuid.uuid4())
    glb_0 = f"{uuid.uuid4()}.glb"
    glb_1 = f"{uuid.uuid4()}.glb"
    conv_dir = Path(settings.CONVERSIONS_PATH) / temp_dir
    conv_dir.mkdir(parents=True, exist_ok=True)
    (conv_dir / glb_0).write_bytes(b"LOD0")
    (conv_dir / glb_1).write_bytes(b"LOD1")
    conversion_service.handle_callback(db, WS, num, "A",
        ConversionResultDTO(
            tempDir=temp_dir,
            convertedFileLODs={"0": glb_0, "1": glb_1},
            box=[0, 0, 0, 2, 2, 2],
        ))
    db.commit()
    conv = svc.get_conversion(db, WS, num, "A", 1)
    assert conv.succeed is True
    br0 = db.query(BinaryResource).filter(
        BinaryResource.full_name == f"{WS}/parts/{num}/A/1/{glb_0}").first()
    br1 = db.query(BinaryResource).filter(
        BinaryResource.full_name == f"{WS}/parts/{num}/A/1/{glb_1}").first()
    assert br0 is not None and br0.quality == 0
    assert br1 is not None and br1.quality == 1
    glb0_path = Path(settings.VAULT_PATH) / WS / "parts" / num / "A" / "1" / glb_0
    glb1_path = Path(settings.VAULT_PATH) / WS / "parts" / num / "A" / "1" / glb_1
    assert glb0_path.exists()
    assert glb1_path.exists()
    # 清理
    cleanup_lod(db, num, "A", 1, [glb_0, glb_1], conv_dir)
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")


def test_callback_materials_saved_as_attached(db):
    """Fix 4: 材质文件保存为附件。"""
    num = "P1BCV-MATL-1"
    _make_part_with_conversion(db, num)
    temp_dir = str(uuid.uuid4())
    glb_name = f"{uuid.uuid4()}.glb"
    mtl_name = f"{uuid.uuid4()}.mtl"
    conv_dir = Path(settings.CONVERSIONS_PATH) / temp_dir
    conv_dir.mkdir(parents=True, exist_ok=True)
    (conv_dir / glb_name).write_bytes(b"GLBDATA")
    (conv_dir / mtl_name).write_bytes(b"MTLDATA")
    conversion_service.handle_callback(db, WS, num, "A",
        ConversionResultDTO(
            tempDir=temp_dir,
            convertedFileLODs={"0": glb_name},
            materials=[mtl_name],
            box=[0, 0, 0, 1, 1, 1],
        ))
    db.commit()
    conv = svc.get_conversion(db, WS, num, "A", 1)
    assert conv.succeed is True
    # 附件保存成功
    att_fn = f"{WS}/parts/{num}/A/1/attachedfiles/{mtl_name}"
    br = db.query(BinaryResource).filter(BinaryResource.full_name == att_fn).first()
    assert br is not None
    assert vault.part_attached_path(WS, num, "A", 1, mtl_name).read_bytes() == b"MTLDATA"
    # 清理
    cleanup_attached(db, num, "A", 1, mtl_name)
    cleanup_lod(db, num, "A", 1, [glb_name], conv_dir)
    db.commit()
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")


def test_sync_assembly_creates_cad_instances(db):
    """Fix 1: 装配位置同步 — 创建 PartUsageLink + CADInstance。"""
    num_parent = "P1BCV-ASM-P1"
    num_child = "P1BCV-ASM-C1"
    child_cad_file = f"{num_child}.stp"

    # 先清理
    from app.models.part import part_iteration_usagelink as piu
    from sqlalchemy import text
    for n in [num_parent, num_child]:
        db.query(Conversion).filter(
            Conversion.workspace_id == WS,
            Conversion.partmaster_partnumber == n,
        ).delete()
        db.execute(piu.delete().where(piu.c.workspace_id == WS,
                                       piu.c.partmaster_partnumber == n))
        db.execute(part_iteration_geometry.delete().where(
            part_iteration_geometry.c.workspace_id == WS,
            part_iteration_geometry.c.partmaster_partnumber == n,
        ))
        db.execute(part_iteration_binres.delete().where(
            part_iteration_binres.c.workspace_id == WS,
            part_iteration_binres.c.partmaster_partnumber == n,
        ))
        # 清理作为组件引用的 partusagelink（含 cadinstance 级联）
        link_rows = db.execute(
            text("SELECT pl.id, plc.cadinstance_id FROM partusagelink pl "
                 "LEFT JOIN partusagelink_cadinstance plc ON plc.partusagelink_id = pl.id "
                 "WHERE pl.component_workspace_id=:ws AND pl.component_partnumber=:pn"),
            {"ws": WS, "pn": n},
        ).fetchall()
        # 先收集 cadinstance_id
        cad_ids = list({row[1] for row in link_rows if row[1] is not None})
        link_ids = list({row[0] for row in link_rows})
        # 删除关联表
        for lid in link_ids:
            db.execute(text("DELETE FROM partusagelink_cadinstance WHERE partusagelink_id=:lid"), {"lid": lid})
        # 删除 orphan cadinstance
        for cid in cad_ids:
            db.execute(text("DELETE FROM cadinstance WHERE id=:cid"), {"cid": cid})
        # 删除 partusagelink
        for lid in link_ids:
            db.execute(text("DELETE FROM partusagelink WHERE id=:lid"), {"lid": lid})
        # 删除作为组件的 PartUsageLink（避免 FK 冲突删除 PartMaster）
        db.query(PartUsageLink).filter(
            PartUsageLink.component_workspace_id == WS,
            PartUsageLink.component_partnumber == n,
        ).delete()
        # 先删 PartIteration（解除 native_cad_file_fullname FK），再删 BinaryResource
        db.query(PartIteration).filter(
            PartIteration.workspace_id == WS,
            PartIteration.partmaster_partnumber == n,
        ).delete()
        db.query(BinaryResource).filter(
            BinaryResource.full_name.like(f'{WS}/parts/{n}%'),
        ).delete()
        db.query(PartRevision).filter(
            PartRevision.workspace_id == WS,
            PartRevision.partmaster_partnumber == n,
        ).delete()
        db.query(PartMaster).filter(
            PartMaster.workspace_id == WS,
            PartMaster.number == n,
        ).delete()
    db.commit()

    from app.schemas.part import PartCreationDTO
    svc.create_part(db, WS, "test1", PartCreationDTO(number=num_parent, name="Assembly"))
    svc.create_part(db, WS, "test1", PartCreationDTO(number=num_child, name="Child"))

    # 给子零件写入 nativecad（以建立 CAD 文件名→PartMaster 映射）
    from app.services.file_service import save_nativecad
    save_nativecad(db, WS, num_child, "A", 1, child_cad_file, b"dummy stp content")
    db.commit()

    # 给父零件创建 pending conversion
    svc.create_conversion(db, WS, num_parent, "A", 1)
    db.commit()

    # 构造 componentPositionMap
    position = PositionDTO(
        translation=[10.0, 20.0, 30.0],
        rotationmatrix=[
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
    )
    temp_dir = str(uuid.uuid4())
    glb_name = f"{uuid.uuid4()}.glb"
    conv_dir = Path(settings.CONVERSIONS_PATH) / temp_dir
    conv_dir.mkdir(parents=True, exist_ok=True)
    (conv_dir / glb_name).write_bytes(b"GLBDATA")

    conversion_service.handle_callback(db, WS, num_parent, "A",
        ConversionResultDTO(
            tempDir=temp_dir,
            convertedFileLODs={"0": glb_name},
            componentPositionMap={child_cad_file: [position]},
            box=[0, 0, 0, 1, 1, 1],
        ))
    db.commit()

    conv = svc.get_conversion(db, WS, num_parent, "A", 1)
    assert conv.succeed is True

    # 验证 PartUsageLink 已创建并关联到父迭代
    from app.models.part import part_iteration_usagelink
    link_rows = db.execute(
        part_iteration_usagelink.select().where(
            part_iteration_usagelink.c.workspace_id == WS,
            part_iteration_usagelink.c.partmaster_partnumber == num_parent,
            part_iteration_usagelink.c.partrevision_version == "A",
            part_iteration_usagelink.c.iteration == 1,
        )
    ).all()
    assert len(link_rows) == 1
    link_id = link_rows[0].component_id

    link = db.query(PartUsageLink).filter(PartUsageLink.id == link_id).first()
    assert link is not None
    assert link.amount == 1
    assert link.component_partnumber == num_child

    # 验证 CADInstance 已创建
    cad_rows = db.execute(
        usage_link_cadinstances.select().where(
            usage_link_cadinstances.c.partusagelink_id == link_id,
        )
    ).all()
    assert len(cad_rows) == 1
    cad = db.query(CADInstance).filter(
        CADInstance.id == cad_rows[0].cadinstance_id).first()
    assert cad is not None
    assert cad.rotation_type == "MATRIX"
    assert cad.tx == 10.0
    assert cad.ty == 20.0
    assert cad.tz == 30.0
    assert cad.m00 == 1.0

    # 清理
    cleanup_assembly(db, num_parent, num_child, "A", 1, glb_name, child_cad_file, conv_dir)
    svc.checkin(db, WS, num_parent, "A", "test1")
    svc.checkin(db, WS, num_child, "A", "test1")
    svc.delete_revision(db, WS, num_parent, "A", "test1")
    svc.delete_revision(db, WS, num_child, "A", "test1")


def test_find_master_by_cad_filename(db):
    """验证 find_part_master_by_cad_filename 能通过 CAD 文件名找到 PartMaster。"""
    num = "P1BCV-FIND-1"
    cad_file = f"{num}.stp"
    for n in [num]:
        db.query(PartIteration).filter(
            PartIteration.workspace_id == WS,
            PartIteration.partmaster_partnumber == n,
        ).delete()
        db.query(PartRevision).filter(
            PartRevision.workspace_id == WS,
            PartRevision.partmaster_partnumber == n,
        ).delete()
        db.query(PartMaster).filter(
            PartMaster.workspace_id == WS,
            PartMaster.number == n,
        ).delete()
        db.query(BinaryResource).filter(
            BinaryResource.full_name.like(f'{WS}/parts/{n}%'),
        ).delete()
    db.commit()
    from app.schemas.part import PartCreationDTO
    from app.services.file_service import save_nativecad
    svc.create_part(db, WS, "test1", PartCreationDTO(number=num, name="find_test"))
    save_nativecad(db, WS, num, "A", 1, cad_file, b"test content")
    db.commit()

    master = svc.find_part_master_by_cad_filename(db, WS, cad_file)
    assert master is not None
    assert master.number == num

    # 不存在的应返回 None
    assert svc.find_part_master_by_cad_filename(db, WS, "nonexistent.stp") is None

    # 清理
    cleanup_simple(db, num, "A", 1, cad_file)


def test_existing_pending_conversion(db):
    """Fix 2: find_pending_conversion 正确返回已经 pending 的 Conversion。"""
    num = "P1BCV-DUP-1"
    _make_part_with_conversion(db, num)
    conv = conversion_service.find_pending_conversion(db, WS, num, "A")
    assert conv is not None
    assert conv.pending is True
    assert conv.partmaster_partnumber == num
    # 结束后不再找到
    conversion_service.end_conversion(db, conv, True)
    assert conversion_service.find_pending_conversion(db, WS, num, "A") is None
    db.delete(conv)
    db.commit()
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")


# ── 清理辅助函数 ──────────────────────────────────────────────

def cleanup_lod(db, num, ver, iteration, glb_names, conv_dir):
    for gn in glb_names:
        db.execute(part_iteration_geometry.delete().where(
            part_iteration_geometry.c.workspace_id == WS,
            part_iteration_geometry.c.partmaster_partnumber == num,
            part_iteration_geometry.c.partrevision_version == ver,
            part_iteration_geometry.c.iteration == iteration,
            part_iteration_geometry.c.geometry_fullname == f"{WS}/parts/{num}/{ver}/{iteration}/{gn}",
        ))
        br = db.query(BinaryResource).filter(
            BinaryResource.full_name == f"{WS}/parts/{num}/{ver}/{iteration}/{gn}",
        ).first()
        if br:
            db.delete(br)
        path = Path(settings.VAULT_PATH) / WS / "parts" / num / ver / str(iteration) / gn
        if path.exists():
            os.remove(path)
    db.query(Conversion).filter(
        Conversion.workspace_id == WS,
        Conversion.partmaster_partnumber == num,
    ).delete()
    db.commit()
    shutil.rmtree(conv_dir, ignore_errors=True)


def cleanup_attached(db, num, ver, iteration, filename):
    db.execute(part_iteration_binres.delete().where(
        part_iteration_binres.c.workspace_id == WS,
        part_iteration_binres.c.partmaster_partnumber == num,
        part_iteration_binres.c.partrevision_version == ver,
        part_iteration_binres.c.iteration == iteration,
        part_iteration_binres.c.attachedfile_fullname
        == f"{WS}/parts/{num}/{ver}/{iteration}/attachedfiles/{filename}",
    ))
    br = db.query(BinaryResource).filter(
        BinaryResource.full_name
        == f"{WS}/parts/{num}/{ver}/{iteration}/attachedfiles/{filename}",
    ).first()
    if br:
        db.delete(br)
    db.commit()


def cleanup_assembly(db, num_parent, num_child, ver, iteration, glb_name,
                     child_cad_file, conv_dir):
    from app.models.part import part_iteration_usagelink as piu
    # 清理 linkage
    link_rows = db.execute(
        piu.select().where(
            piu.c.workspace_id == WS,
            piu.c.partmaster_partnumber == num_parent,
            piu.c.partrevision_version == ver,
            piu.c.iteration == iteration,
        )
    ).all()
    for row in link_rows:
        cad_rows = db.execute(
            usage_link_cadinstances.select().where(
                usage_link_cadinstances.c.partusagelink_id == row.component_id,
            )
        ).all()
        for cr in cad_rows:
            db.execute(usage_link_cadinstances.delete().where(
                usage_link_cadinstances.c.partusagelink_id == row.component_id,
                usage_link_cadinstances.c.cadinstance_id == cr.cadinstance_id,
            ))
            db.query(CADInstance).filter(
                CADInstance.id == cr.cadinstance_id,
            ).delete()
        db.execute(piu.delete().where(
            piu.c.component_id == row.component_id,
        ))
        db.query(PartUsageLink).filter(
            PartUsageLink.id == row.component_id,
        ).delete()
    # 清理 geometry
    gn = f"{WS}/parts/{num_parent}/{ver}/{iteration}/{glb_name}"
    db.execute(part_iteration_geometry.delete().where(
        part_iteration_geometry.c.geometry_fullname == gn,
    ))
    br = db.query(BinaryResource).filter(BinaryResource.full_name == gn).first()
    if br:
        db.delete(br)
    path = Path(settings.VAULT_PATH) / WS / "parts" / num_parent / ver / str(iteration) / glb_name
    if path.exists():
        os.remove(path)
    # 清理 conversion
    db.query(Conversion).filter(
        Conversion.workspace_id == WS,
        Conversion.partmaster_partnumber == num_parent,
    ).delete()
    # 清理 child nativecad（先清 FK 再删 BinaryResource）
    child_fn = f"{WS}/parts/{num_child}/A/1/nativecad/{child_cad_file}"
    db.query(PartIteration).filter(
        PartIteration.workspace_id == WS,
        PartIteration.partmaster_partnumber == num_child,
        PartIteration.partrevision_version == "A",
        PartIteration.iteration == 1,
    ).update({"native_cad_file_fullname": None}, synchronize_session=False)
    db.query(BinaryResource).filter(
        BinaryResource.full_name == child_fn,
    ).delete()
    db.commit()
    shutil.rmtree(conv_dir, ignore_errors=True)


def cleanup_simple(db, num, ver, iteration, cad_file):
    # 先清除 PartIteration.native_cad_file_fullname FK 引用，再删 BinaryResource
    db.query(PartIteration).filter(
        PartIteration.workspace_id == WS,
        PartIteration.partmaster_partnumber == num,
    ).update({"native_cad_file_fullname": None}, synchronize_session=False)
    db.query(BinaryResource).filter(
        BinaryResource.full_name
        == f"{WS}/parts/{num}/{ver}/{iteration}/nativecad/{cad_file}",
    ).delete()
    db.query(PartIteration).filter(
        PartIteration.workspace_id == WS,
        PartIteration.partmaster_partnumber == num,
    ).delete()
    db.query(PartRevision).filter(
        PartRevision.workspace_id == WS,
        PartRevision.partmaster_partnumber == num,
    ).delete()
    db.query(PartMaster).filter(
        PartMaster.workspace_id == WS,
        PartMaster.number == num,
    ).delete()
    db.commit()
