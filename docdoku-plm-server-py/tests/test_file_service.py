"""file_service 测试：vault 写读 + BinaryResource 记录。"""
import os
from app.services import file_service
from app.services.product_service import ProductService
from app.models.part import BinaryResource

WS = "Workspace_2"
svc = ProductService()


def _make_part(db, num):
    from app.schemas.part import PartCreationDTO
    return svc.create_part(db, WS, "test1",
                           PartCreationDTO(number=num, name="t"))


def test_save_nativecad_writes_vault_and_binaryresource(db):
    num = "P1BFS-NATIVE-1"
    _make_part(db, num)
    br = file_service.save_nativecad(db, WS, num, "A", 1,
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
    os.remove(p)


def test_get_file_bytes_reads_back(db):
    num = "P1BFS-READ-1"
    _make_part(db, num)
    file_service.save_nativecad(db, WS, num, "A", 1, "m.stp", b"HELLO")
    db.commit()
    data = file_service.get_file_bytes(WS, num, "A", 1, "nativecad", "m.stp")
    assert data == b"HELLO"
    from app.services import vault
    p = vault.part_nativecad_path(WS, num, "A", 1, "m.stp")
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")
    os.remove(p)
