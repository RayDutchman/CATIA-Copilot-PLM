"""杂项端点：语言、时区、平台健康检查。"""
from fastapi import APIRouter

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
def platform_health():
    return {"executionTime": 0, "status": "UP"}

