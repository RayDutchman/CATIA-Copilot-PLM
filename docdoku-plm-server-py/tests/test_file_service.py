"""file_service 测试：vault 写读 + BinaryResource 记录。"""
from app.services import binary_storage
from app.services.product_manager import ProductService
from app.models.part import BinaryResource

WS = "Workspace_2"
svc = ProductService()


def _make_part(db, num):
    from app.schemas.part import PartCreationDTO
    from app.models.part import Conversion, PartIteration, PartRevision, PartMaster, BinaryResource, part_iteration_geometry
    # 预清理
    db.query(Conversion).filter(
        Conversion.workspace_id == WS,
        Conversion.partmaster_partnumber == num,
    ).delete()
    db.execute(part_iteration_geometry.delete().where(
        part_iteration_geometry.c.workspace_id == WS,
        part_iteration_geometry.c.partmaster_partnumber == num,
    ))
    db.query(BinaryResource).filter(
        BinaryResource.full_name.like(f'{WS}/parts/{num}%'),
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
    return svc.create_part(db, WS, "test1",
                           PartCreationDTO(number=num, name="t"))


def test_save_nativecad_writes_vault_and_binaryresource(db, temp_vault):
    num = "P1BFS-NATIVE-1"
    _make_part(db, num)
    br = binary_storage.save_nativecad(db, WS, num, "A", 1,
                                     "m.stp", b"STEPDATA")
    db.commit()
    assert br.full_name == f"{WS}/parts/{num}/A/1/nativecad/m.stp"
    assert br.dtype == "BinaryResource"
    from app.services import vault
    p = vault.part_nativecad_path(WS, num, "A", 1, "m.stp")
    assert p.read_bytes() == b"STEPDATA"
    it = next(i for i in svc.get_revision(db, WS, num, "A").iterations
              if i.iteration == 1)
    assert it.native_cad_file_fullname == br.full_name
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")


def test_get_file_bytes_reads_back(db, temp_vault):
    num = "P1BFS-READ-1"
    _make_part(db, num)
    binary_storage.save_nativecad(db, WS, num, "A", 1, "m.stp", b"HELLO")
    db.commit()
    data = binary_storage.get_file_bytes(WS, num, "A", 1, "nativecad", "m.stp")
    assert data == b"HELLO"
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")
