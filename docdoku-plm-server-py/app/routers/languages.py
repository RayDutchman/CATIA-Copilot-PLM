from typing import List
from fastapi import APIRouter
from app.core.i18n import SUPPORTED_LANGUAGES

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


@router.get("/languages", response_model=List[str])
@router.get("/languages/", include_in_schema=False)
def list_languages():
    return SUPPORTED_LANGUAGES
