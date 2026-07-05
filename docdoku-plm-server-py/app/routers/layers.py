"""产品图层与标记（Layer / Marker）端点路由。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.product import Layer, Marker

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


# ── Layers ──

@router.get("/workspaces/{ws}/products/{pid}/layers")
@router.get("/workspaces/{ws}/products/{pid}/layers/", include_in_schema=False)
def list_layers(ws: str, pid: str,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    layers = db.query(Layer).filter(
        Layer.workspace_id == ws,
        Layer.configurationitem_id == pid,
    ).all()
    return [{"id": l.id, "name": l.name, "workspaceId": l.workspace_id,
             "configurationItemId": l.configurationitem_id} for l in layers]


@router.post("/workspaces/{ws}/products/{pid}/layers", status_code=201)
@router.post("/workspaces/{ws}/products/{pid}/layers/", status_code=201, include_in_schema=False)
def create_layer(ws: str, pid: str, body: dict,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    layer = Layer(workspace_id=ws, configurationitem_id=pid,
                  name=body.get("name", ""))
    db.add(layer); db.commit(); db.refresh(layer)
    return {"id": layer.id, "name": layer.name, "workspaceId": layer.workspace_id,
            "configurationItemId": layer.configurationitem_id}


@router.put("/workspaces/{ws}/products/{pid}/layers/{layer_id}")
@router.put("/workspaces/{ws}/products/{pid}/layers/{layer_id}/", include_in_schema=False)
def update_layer(ws: str, pid: str, layer_id: int, body: dict,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    layer = db.query(Layer).filter(
        Layer.id == layer_id, Layer.workspace_id == ws,
        Layer.configurationitem_id == pid,
    ).first()
    if not layer:
        raise HTTPException(404, "Layer not found")
    if "name" in body:
        layer.name = body["name"]
    db.commit(); db.refresh(layer)
    return {"id": layer.id, "name": layer.name, "workspaceId": layer.workspace_id,
            "configurationItemId": layer.configurationitem_id}


@router.delete("/workspaces/{ws}/products/{pid}/layers/{layer_id}", status_code=204)
@router.delete("/workspaces/{ws}/products/{pid}/layers/{layer_id}/", status_code=204, include_in_schema=False)
def delete_layer(ws: str, pid: str, layer_id: int,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    layer = db.query(Layer).filter(
        Layer.id == layer_id, Layer.workspace_id == ws,
        Layer.configurationitem_id == pid,
    ).first()
    if not layer:
        return Response(status_code=204)
    db.execute(sql_text("DELETE FROM marker WHERE layer_id=:lid"), {"lid": layer_id})
    db.delete(layer)
    db.commit()
    return Response(status_code=204)


# ── Markers ──

@router.get("/workspaces/{ws}/products/{pid}/layers/{layer_id}/markers")
@router.get("/workspaces/{ws}/products/{pid}/layers/{layer_id}/markers/", include_in_schema=False)
def list_markers(ws: str, pid: str, layer_id: int,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    markers = db.query(Marker).filter(Marker.layer_id == layer_id).all()
    return [{"id": m.id, "x": m.x, "y": m.y, "z": m.z,
             "title": m.title or "", "description": m.description or "",
             "layerId": m.layer_id} for m in markers]


@router.post("/workspaces/{ws}/products/{pid}/layers/{layer_id}/markers", status_code=201)
@router.post("/workspaces/{ws}/products/{pid}/layers/{layer_id}/markers/", status_code=201, include_in_schema=False)
def create_marker(ws: str, pid: str, layer_id: int, body: dict,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    layer = db.query(Layer).filter(
        Layer.id == layer_id, Layer.workspace_id == ws,
        Layer.configurationitem_id == pid,
    ).first()
    if not layer:
        raise HTTPException(404, "Layer not found")
    marker = Marker(
        x=body.get("x", 0), y=body.get("y", 0), z=body.get("z", 0),
        title=body.get("title", ""), description=body.get("description", ""),
        layer_id=layer_id,
    )
    db.add(marker); db.commit(); db.refresh(marker)
    return {"id": marker.id, "x": marker.x, "y": marker.y, "z": marker.z,
            "title": marker.title or "", "description": marker.description or "",
            "layerId": marker.layer_id}
