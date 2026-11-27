from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.transaction_history import (
    add_transaction,
    get_transaction_history
)

router = APIRouter(
    prefix="/history",
    tags=["Secure Transaction History"]
)


class TransactionRecord(BaseModel):
    user_id: str
    transaction_id: str
    amount: float
    transaction_type: str
    status: str


@router.post("/add")
def save_transaction(request: TransactionRecord):

    try:
        result = add_transaction(
            request.user_id,
            request.transaction_id,
            request.amount,
            request.transaction_type,
            request.status
        )

        return {
            "success": True,
            "message": "Transaction saved successfully",
            "transaction": result
        }

    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/{user_id}")
def view_transaction_history(user_id: str):

    history = get_transaction_history(user_id)

    return {
        "user_id": user_id,
        "total_transactions": len(history),
        "transactions": history
    }