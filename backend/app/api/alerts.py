from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.database.models import Alert, Transaction

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/")
def list_alerts(status: str | None = Query(default=None, pattern="^(open|acknowledged|resolved)$"),
                limit: int = Query(default=10, ge=1, le=100),
                db: Session = Depends(get_db)):
    query = select(Alert).options(
        joinedload(Alert.transaction).joinedload(Transaction.risk_assessment)
    ).order_by(Alert.id.desc())
    if status:
        query = query.where(Alert.status == status)
    query = query.limit(limit)
    return [{
        "id": alert.id,
        "transaction_id": alert.transaction_id,
        "transaction_ref": alert.transaction.transaction_id,
        "amount": alert.transaction.amount,
        "title": alert.title,
        "severity": alert.severity,
        "status": alert.status,
        "created_at": alert.created_at,
        "risk_level": (
            alert.transaction.risk_assessment.risk_level
            if alert.transaction.risk_assessment else None
        ),
        "fraud_probability": (
            alert.transaction.risk_assessment.fraud_probability
            if alert.transaction.risk_assessment else None
        ),
        "model_classification": (
            alert.transaction.risk_assessment.model_classification
            if alert.transaction.risk_assessment else None
        ),
        "explanation": (
            alert.transaction.risk_assessment.explanation
            if alert.transaction.risk_assessment else "Risk assessment unavailable."
        ),
    } for alert in db.scalars(query).unique().all()]


@router.patch("/{alert_id}")
def update_alert(alert_id: int, status: str, db: Session = Depends(get_db)):
    if status not in {"open", "acknowledged", "resolved"}:
        raise HTTPException(status_code=422, detail="Status must be open, acknowledged, or resolved.")
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert.status = status
    db.commit()
    return {"id": alert.id, "status": alert.status}