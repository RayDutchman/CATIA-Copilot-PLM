import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/platform/health")
@router.get("/platform/health/", include_in_schema=False)
def platform_health(db: Session = Depends(get_db)):
    start = time.time()
    try:
        db.execute(text("SELECT 1")).scalar()
        elapsed = int((time.time() - start) * 1000)
        return {"executionTime": elapsed, "status": "ok"}
    except Exception:
        return {"executionTime": 0, "status": "error"}
