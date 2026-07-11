"""零件状态管理测试：release/obsolete/newVersion。"""
from fastapi.testclient import TestClient
from app.main import app
from app.core import i18n
from app.core.database import SessionLocal
from app.models.part import (
    PartMaster, PartRevision, PartIteration, Conversion,
    BinaryResource, part_iteration_geometry, part_iteration_binres,
)

PREFIX = "/docdoku-plm-server-rest/api"
WS = "GD50"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login",
                    json={"login": "test1", "password": "password"})
    return r.headers.get("jwt")


def _create(num, h):
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "t"}, headers=h)


def _pre_cleanup(num):
    db = SessionLocal()
    try:
        db.query(Conversion).filter(
            Conversion.workspace_id == WS,
            Conversion.partmaster_partnumber == num,
        ).delete()
        db.execute(part_iteration_geometry.delete().where(
            part_iteration_geometry.c.workspace_id == WS,
            part_iteration_geometry.c.partmaster_partnumber == num,
        ))
        db.execute(part_iteration_binres.delete().where(
            part_iteration_binres.c.workspace_id == WS,
            part_iteration_binres.c.partmaster_partnumber == num,
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
    finally:
        db.close()


def _cleanup(num, h, ver="A"):
    _pre_cleanup(num)
    # also try via API
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/parts/{num}-{ver}", headers=h)


def test_release_checked_out_returns_400():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BST-REL-1"; _pre_cleanup(num); _create(num, h)
    # 新建即签出，直接 release 应报已签出 46
    resp = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/release", headers=h)
    assert resp.status_code == 400
    assert resp.text == i18n.get("NotAllowedException46", "zh")
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    _cleanup(num, h)


def test_release_then_obsolete_succeeds():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BST-OBS-1"; _pre_cleanup(num); _create(num, h)
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    rel = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/release", headers=h)
    assert rel.status_code == 200
    assert rel.json()["status"] == "RELEASED"
    obs = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/obsolete", headers=h)
    assert obs.status_code == 200
    assert obs.json()["status"] == "OBSOLETE"
    _cleanup(num, h)


def test_obsolete_unreleased_returns_400():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BST-OBSU-1"; _pre_cleanup(num); _create(num, h)
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    resp = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/obsolete", headers=h)
    assert resp.status_code == 400
    assert resp.text == i18n.get("NotAllowedException36", "zh")
    _cleanup(num, h)
