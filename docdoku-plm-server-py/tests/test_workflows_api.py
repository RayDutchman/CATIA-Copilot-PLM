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


def _h():
    return {"Authorization": f"Bearer {_token()}"}


def test_create_and_delete_workflow_model():
    model_id = "WFM-" + uuid.uuid4().hex[:6]
    resp = client.post(f"{PREFIX}/workspaces/{WS}/workflow-models",
                       json={"id": model_id, "finalLifecycleState": "RELEASED"},
                       headers=_h())
    assert resp.status_code == 201
    assert resp.json()["id"] == model_id

    resp = client.get(f"{PREFIX}/workspaces/{WS}/workflow-models/{model_id}", headers=_h())
    assert resp.status_code == 200

    resp = client.delete(f"{PREFIX}/workspaces/{WS}/workflow-models/{model_id}", headers=_h())
    assert resp.status_code == 204
