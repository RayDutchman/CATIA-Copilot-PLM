from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from sqlalchemy import text

client = TestClient(app)
PREFIX = "/docdoku-plm-server-rest/api"


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.headers.get("jwt", "")


def test_acknowledge_notification():
    db = SessionLocal()
    try:
        row = db.execute(text(
            "SELECT id FROM modificationnotification LIMIT 1"
        )).first()
        if not row:
            return
        nid = row[0]
        resp = client.put(f"{PREFIX}/workspaces/Workspace_2/notifications/{nid}",
                          json={"ackComment": "test"},
                          headers={"Authorization": f"Bearer {_token()}"})
        assert resp.status_code == 200
    finally:
        db.close()
