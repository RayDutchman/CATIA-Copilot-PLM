"""标签管理测试。"""
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.part import (
    PartMaster, PartRevision, PartIteration, Conversion,
    BinaryResource, part_iteration_geometry, part_iteration_binres,
)

PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login",
                    json={"login": "test1", "password": "password"})
    return r.headers.get("jwt")


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


def _create(num, h):
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "t"}, headers=h)


def _cleanup(num, h):
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/parts/{num}-A", headers=h)


def test_set_and_get_tags():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BTAG-1"; _pre_cleanup(num); _create(num, h)
    resp = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/tags",
                      json={"tags": ["alpha", "beta"]}, headers=h)
    assert resp.status_code == 200
    assert set(resp.json()["tags"]) == {"alpha", "beta"}
    _cleanup(num, h)


def test_remove_tag():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BTAG-2"; _pre_cleanup(num); _create(num, h)
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/tags",
               json={"tags": ["x", "y"]}, headers=h)
    resp = client.request("DELETE",
                          f"{PREFIX}/workspaces/{WS}/parts/{num}-A/tags/x",
                          headers=h)
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["y"]
    _cleanup(num, h)
