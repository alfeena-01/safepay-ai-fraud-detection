from fastapi import APIRouter
from pydantic import BaseModel

from app.services.voice_support import get_voice_support_response

router = APIRouter(
    prefix="/voice",
    tags=["Voice-Based Customer Support"]
)


class VoiceSupportRequest(BaseModel):
    message: str


@router.post("/support")
def voice_support(request: VoiceSupportRequest):

    response = get_voice_support_response(request.message)

    return {
        "success": True,
        "user_message": request.message,
        "support_response": response
    }