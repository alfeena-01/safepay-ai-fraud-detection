from fastapi import APIRouter
from pydantic import BaseModel

from app.services.multilingual_support import (
    get_message,
    get_supported_languages
)

router = APIRouter(prefix="/language", tags=["Multi-Language Support"])


class LanguageRequest(BaseModel):
    language: str
    message_key: str


@router.get("/supported")
def supported_languages():
    return {
        "supported_languages": get_supported_languages()
    }


@router.post("/translate")
def translate_message(request: LanguageRequest):

    message = get_message(
        request.language,
        request.message_key
    )

    return {
        "language": request.language,
        "message": message
    }