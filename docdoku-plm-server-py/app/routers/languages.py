from fastapi import APIRouter
from app.core.i18n import SUPPORTED_LANGUAGES

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/languages")
@router.get("/languages/", include_in_schema=False)
def list_languages():
    return SUPPORTED_LANGUAGES
