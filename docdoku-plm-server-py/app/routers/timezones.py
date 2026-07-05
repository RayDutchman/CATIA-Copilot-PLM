from fastapi import APIRouter

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/timezones")
@router.get("/timezones/", include_in_schema=False)
def list_timezones():
    return ["UTC", "Asia/Shanghai", "Europe/Paris", "America/New_York"]
