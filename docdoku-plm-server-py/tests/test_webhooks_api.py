import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
PREFIX = "/docdoku-plm-server-rest/api"
WS = "GD50"


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.headers["jwt"]


def test_create_and_delete_webhook():
    h = {"Authorization": f"Bearer {_token()}"}
    name = "WH-" + uuid.uuid4().hex[:6]
    resp = client.post(f"{PREFIX}/workspaces/{WS}/webhooks",
                       json={"name": name, "active": True,
                             "webhookApp": {"dtype": "SIMPLE_HTTP", "uri": "http://example.com"}},
                       headers=h)
    assert resp.status_code == 201
    wid = resp.json()["id"]
    resp = client.delete(f"{PREFIX}/workspaces/{WS}/webhooks/{wid}", headers=h)
    assert resp.status_code == 204
