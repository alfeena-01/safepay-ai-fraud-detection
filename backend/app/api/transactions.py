from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.database.models import Alert, RiskAssessment, Transaction
from app.database.schemas import RiskRead, TransactionRead
from app.services.anomaly_detection_engine.risk_scoring import assess_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=list[TransactionRead])
def list_transactions(
    q: str | None = None,
    transaction_type: str | None = None,
    risk_level: str | None = Query(default=None, pattern="^(low|medium|high)$"),
    fraud_only: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(Transaction).options(joinedload(Transaction.risk_assessment))
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(
            Transaction.transaction_id.ilike(term),
            Transaction.name_orig.ilike(term),
            Transaction.name_dest.ilike(term),
        ))
    if transaction_type:
        query = query.where(Transaction.transaction_type == transaction_type.upper())
    if fraud_only is not None:
        query = query.where(Transaction.is_fraud.is_(fraud_only))
    if risk_level:
        query = query.join(RiskAssessment).where(RiskAssessment.risk_level == risk_level)
    return db.scalars(query.order_by(Transaction.id.desc()).offset(offset).limit(limit)).unique().all()


@router.get("/{transaction_id}")
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.scalar(
        select(Transaction).options(joinedload(Transaction.risk_assessment)).where(Transaction.id == transaction_id)
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    result = TransactionRead.model_validate(transaction).model_dump(mode="json")
    result["risk_assessment"] = RiskRead.model_validate(transaction.risk_assessment).model_dump(mode="json") \
        if transaction.risk_assessment else None
    return result


@router.post("/{transaction_id}/analyze", response_model=RiskRead)
def analyze_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    result = assess_transaction(transaction)
    assessment = db.scalar(select(RiskAssessment).where(RiskAssessment.transaction_id == transaction.id))
    if assessment is None:
        assessment = RiskAssessment(transaction_id=transaction.id, **result)
        db.add(assessment)
    else:
        for key, value in result.items():
            setattr(assessment, key, value)
    if result["overall_risk_score"] >= 70:
        existing_alert = db.scalar(select(Alert).where(Alert.transaction_id == transaction.id))
        if existing_alert is None:
            db.add(Alert(
                transaction_id=transaction.id,
                title="High-risk transaction requires review",
                severity="high",
            ))
    db.commit()
    db.refresh(assessment)
    return assessment