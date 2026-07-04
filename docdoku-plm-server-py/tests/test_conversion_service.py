"""转换回调服务测试。"""
import os
import uuid
import shutil
from pathlib import Path
from app.services import conversion_service
from app.services.product_service import ProductService
from app.schemas.part import ConversionResultDTO
from app.models.part import (
    BinaryResource, part_iteration_geometry,
    Conversion, PartIteration, PartRevision, PartMaster,
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
    glb_path = vault._vault_root() / WS / "parts" / num / "A" / "1" / glb_name
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
