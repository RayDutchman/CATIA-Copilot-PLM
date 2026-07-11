from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.part import PartMaster
from sqlalchemy import text

PREFIX = "/docdoku-plm-server-rest/api"
WS = "GD50"
client = TestClient(app)


def _cleanup_part(number):
    """删除测试创建的 PartMaster（含其 revisions/iterations）。"""
    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM partiteration WHERE workspace_id=:ws AND partmaster_partnumber=:pn"),
                   {"ws": WS, "pn": number})
        db.execute(text("DELETE FROM partrevision WHERE workspace_id=:ws AND partmaster_partnumber=:pn"),
                   {"ws": WS, "pn": number})
        db.execute(text("DELETE FROM partmaster WHERE workspace_id=:ws AND partnumber=:pn"),
                   {"ws": WS, "pn": number})
        db.commit()
    finally:
        db.close()


def _token():
    r = client.post(f"{PREFIX}/auth/login", json={"login": "test1", "password": "password"})
    return r.headers.get("jwt")


def _headers():
    return {"Authorization": f"Bearer {_token()}"}


def test_generate_id_no_mask_no_existing_parts():
    """无 mask 且无已有零件，返回 {template_id}-001。"""
    h = _headers()
    tid = f"PTGDPT-{hash(_token()) % 100000}"
    # 创建模板（无 mask）
    resp = client.post(
        f"{PREFIX}/workspaces/{WS}/part-templates",
        json={"id": tid, "idGenerated": True},
        headers=h,
    )
    assert resp.status_code == 201

    # 生成 ID
    resp2 = client.get(
        f"{PREFIX}/workspaces/{WS}/part-templates/{tid}/generate_id",
        headers=h,
    )
    assert resp2.status_code == 200
    assert resp2.json() == {"generatedId": f"{tid}-001"}

    # 清理
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/part-templates/{tid}", headers=h)


def test_generate_id_no_mask_with_existing_parts():
    """无 mask 但有已有零件，递增返回下一个序号。"""
    h = _headers()
    tid = f"PTGDPT-{hash(_token() + 'seq') % 100000}"

    # 在数据库中直接插入已有零件
    db = SessionLocal()
    try:
        for seq in [1, 3]:
            db.add(PartMaster(
                workspace_id=WS,
                number=f"{tid}-{seq:03d}",
                name=f"Test Part {seq}",
                type="part",
                author_login="test1",
                author_workspace_id=WS,
            ))
        db.commit()
    finally:
        db.close()

    # 创建模板
    resp = client.post(
        f"{PREFIX}/workspaces/{WS}/part-templates",
        json={"id": tid, "idGenerated": True},
        headers=h,
    )
    assert resp.status_code == 201

    # 生成 ID — 应该是 4（1, 3 中最大值 3 + 1）
    resp2 = client.get(
        f"{PREFIX}/workspaces/{WS}/part-templates/{tid}/generate_id",
        headers=h,
    )
    assert resp2.status_code == 200
    assert resp2.json() == {"generatedId": f"{tid}-004"}

    # 清理
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/part-templates/{tid}", headers=h)
    # 清理零件
    db = SessionLocal()
    try:
        for seq in [1, 3]:
            pm = db.query(PartMaster).filter(
                PartMaster.workspace_id == WS,
                PartMaster.number == f"{tid}-{seq:03d}",
            ).first()
            if pm:
                db.delete(pm)
        db.commit()
    finally:
        db.close()


def test_generate_id_with_mask_no_existing_parts():
    """有 mask 但无已有零件，返回 mask 的首个 ID。"""
    h = _headers()
    tid = f"PTGM-{hash(_token() + 'mask') % 100000}"
    mask = "CA_#####"

    resp = client.post(
        f"{PREFIX}/workspaces/{WS}/part-templates",
        json={"id": tid, "mask": mask, "idGenerated": True},
        headers=h,
    )
    assert resp.status_code == 201

    resp2 = client.get(
        f"{PREFIX}/workspaces/{WS}/part-templates/{tid}/generate_id",
        headers=h,
    )
    assert resp2.status_code == 200
    assert resp2.json() == {"generatedId": "CA_00000"}

    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/part-templates/{tid}", headers=h)


def test_generate_id_with_mask_increment():
    """有 mask 且有已有零件，递增返回下一个。"""
    _cleanup_part("CA_00042")  # 清理上次运行的残留数据
    h = _headers()
    tid = f"PTGM-{hash(_token() + 'incr') % 100000}"
    mask = "CA_#####"

    # 插入已有零件 CA_00042
    db = SessionLocal()
    try:
        db.add(PartMaster(
            workspace_id=WS,
            number="CA_00042",
            name="Test Part",
            type="part",
            author_login="test1",
            author_workspace_id=WS,
        ))
        db.commit()
    finally:
        db.close()

    resp = client.post(
        f"{PREFIX}/workspaces/{WS}/part-templates",
        json={"id": tid, "mask": mask, "idGenerated": True},
        headers=h,
    )
    assert resp.status_code == 201

    resp2 = client.get(
        f"{PREFIX}/workspaces/{WS}/part-templates/{tid}/generate_id",
        headers=h,
    )
    assert resp2.status_code == 200
    assert resp2.json() == {"generatedId": "CA_00043"}

    # 清理
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/part-templates/{tid}", headers=h)
    db = SessionLocal()
    try:
        pm = db.query(PartMaster).filter(
            PartMaster.workspace_id == WS,
            PartMaster.number == "CA_00042",
        ).first()
        if pm:
            db.delete(pm)
        db.commit()
    finally:
        db.close()


def test_generate_id_404():
    """不存在的模板返回 404。"""
    h = _headers()
    resp = client.get(
        f"{PREFIX}/workspaces/{WS}/part-templates/NONEXIST-TEMPLATE/generate_id",
        headers=h,
    )
    assert resp.status_code == 404
