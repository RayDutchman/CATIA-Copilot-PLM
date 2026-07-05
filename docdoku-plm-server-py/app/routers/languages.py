from fastapi import APIRouter

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/languages")
@router.get("/languages/", include_in_schema=False)
def list_languages():
    return ["en", "fr", "zh", "ru"]
