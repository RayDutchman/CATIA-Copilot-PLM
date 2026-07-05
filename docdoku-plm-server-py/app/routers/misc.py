"""杂项端点：语言、时区、平台健康检查。"""
import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/languages")
@router.get("/languages/", include_in_schema=False)
def list_languages():
    return ["en", "fr", "zh", "ru"]


@router.get("/timezones")
@router.get("/timezones/", include_in_schema=False)
def list_timezones():
    return ["UTC", "Asia/Shanghai", "Europe/Paris", "America/New_York"]


@router.get("/platform/health")
@router.get("/platform/health/", include_in_schema=False)
def platform_health(db: Session = Depends(get_db)):
    start = time.time()
    try:
        db.execute(text("SELECT 1")).scalar()
        elapsed = int((time.time() - start) * 1000)
        return {"executionTime": elapsed, "status": "UP"}
    except Exception:
        return {"executionTime": 0, "status": "DOWN"}
