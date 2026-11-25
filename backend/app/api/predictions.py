from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import RiskAssessment, Transaction
from app.database.schemas import RiskRead

router = APIRouter(prefix="/predictions", tags=["risk analysis"])


@router.get("/{transaction_id}", response_model=RiskRead)
def get_prediction(transaction_id: str, db: Session = Depends(get_db)):
    assessment = db.scalar(
        select(RiskAssessment)
        .join(Transaction)
        .where(Transaction.transaction_id == transaction_id)
    )
    if assessment is None:
        raise HTTPException(status_code=404, detail="No risk assessment found. Analyze the transaction first.")
    return assessment