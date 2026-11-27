from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.emergency_help import create_emergency_request

router = APIRouter(prefix="/emergency", tags=["Emergency Help"])


class EmergencyRequest(BaseModel):
    user_id: str
    message: str = "Emergency help requested"


@router.post("/help")
def request_emergency_help(request: EmergencyRequest):

    try:
        result = create_emergency_request(
            user_id=request.user_id,
            message=request.message
        )

        return {
            "success": True,
            "emergency": result
        }

    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))