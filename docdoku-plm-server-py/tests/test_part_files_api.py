"""文件上传/下载端点测试。"""
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.core.database import SessionLocal

PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app)


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
    num = "P1BUP-CAD-1"; _create(num, h)
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
    num = "P1BUP-BAD-1"; _create(num, h)
    resp = client.post(
        f"{PREFIX}/files/{WS}/parts/{num}/A/1/nativecad",
        files={"upload": ("m.txt", b"x", "text/plain")}, headers=h)
    assert resp.status_code == 400
    assert "Unsupported CAD file format" in resp.text
    _cleanup(num, h)


def test_upload_download_attached_roundtrip():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BUP-ATT-1"; _create(num, h)
    up = client.post(
        f"{PREFIX}/files/{WS}/parts/{num}/A/1/attachedfiles",
        files={"upload": ("doc.pdf", b"PDFBYTES", "application/pdf")}, headers=h)
    assert up.status_code == 201
    dl = client.get(f"{PREFIX}/files/{WS}/parts/{num}/A/1/attachedfiles/doc.pdf",
                    headers=h)
    assert dl.status_code == 200
    assert dl.content == b"PDFBYTES"
    _cleanup(num, h)
