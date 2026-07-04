"""文件上传/下载端点测试。"""
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.core.database import SessionLocal

PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app)


def _pre_cleanup(num):
    """清理上一次运行中断可能留下的残留数据。"""
    db = SessionLocal()
    try:
        from app.models.part import (
            Conversion, PartIteration, PartRevision, PartMaster,
            BinaryResource, part_iteration_geometry, part_iteration_binres,
        )
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


def _token():
    r = client.post(f"{PREFIX}/auth/login",
                    json={"login": "test1", "password": "password"})
    return r.headers.get("jwt")


def _create(num, h):
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "t"}, headers=h)


def _cleanup(num, h):
    db = SessionLocal()
    try:
        from app.models.part import Conversion
        db.query(Conversion).filter(
            Conversion.workspace_id == WS,
            Conversion.partmaster_partnumber == num,
            Conversion.partrevision_version == "A",
        ).delete()
        db.commit()
    finally:
        db.close()
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/parts/{num}-A", headers=h)


def test_upload_nativecad_triggers_conversion():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BUP-CAD-1"; _pre_cleanup(num); _create(num, h)
    with patch("app.routers.part_files.send_conversion_order") as mock_send:
        resp = client.post(
            f"{PREFIX}/files/{WS}/parts/{num}/A/1/nativecad",
            files={"upload": ("m.stp", b"STEPDATA", "application/octet-stream")},
            headers=h)
    assert resp.status_code == 201
    assert mock_send.called
    assert mock_send.call_args[0][5]
    _cleanup(num, h)


def test_upload_bad_extension_returns_400():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BUP-BAD-1"; _pre_cleanup(num); _create(num, h)
    resp = client.post(
        f"{PREFIX}/files/{WS}/parts/{num}/A/1/nativecad",
        files={"upload": ("m.txt", b"x", "text/plain")}, headers=h)
    assert resp.status_code == 400
    assert "Unsupported CAD file format" in resp.text
    _cleanup(num, h)


def test_upload_download_attached_roundtrip():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BUP-ATT-1"; _pre_cleanup(num); _create(num, h)
    up = client.post(
        f"{PREFIX}/files/{WS}/parts/{num}/A/1/attachedfiles",
        files={"upload": ("doc.pdf", b"PDFBYTES", "application/pdf")}, headers=h)
    assert up.status_code == 201
    dl = client.get(f"{PREFIX}/files/{WS}/parts/{num}/A/1/attachedfiles/doc.pdf",
                    headers=h)
    assert dl.status_code == 200
    assert dl.content == b"PDFBYTES"
    _cleanup(num, h)
