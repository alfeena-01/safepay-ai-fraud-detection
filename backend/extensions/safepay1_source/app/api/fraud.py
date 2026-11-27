from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd

from app.services.fraud_detection_service import (
    train_fraud_detection_model,
    check_transaction
)

from app.services.smart_fraud_alert import generate_fraud_alert

router = APIRouter(prefix="/fraud", tags=["Fraud Detection"])

fraud_model = None


class Transaction(BaseModel):
    step: int
    type: str
    amount: float
    oldbalanceOrg: float
    newbalanceOrig: float
    oldbalanceDest: float = 0
    newbalanceDest: float = 0


@router.post("/train")
def train_model():
    global fraud_model

    try:
        fraud_model, results = train_fraud_detection_model(
            "data/raw/transactions.csv"
        )

        return {
            "message": "Fraud detection model trained successfully",
            "results": results
        }

    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/predict")
def predict_transaction(transaction: Transaction):

    if fraud_model is None:
        raise HTTPException(
            status_code=400,
            detail="Please train the model first."
        )

    data = pd.DataFrame([transaction.model_dump()])

    try:
        result = check_transaction(fraud_model, data)

        alert = generate_fraud_alert(
            result,
            amount=transaction.amount
        )

        return {
            "prediction": result,
            "fraud_alert": alert
        }

    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))