from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Alert, RiskAssessment, Transaction

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics")
def dashboard_metrics(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Transaction.id))) or 0
    amount = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0.0))) or 0.0
    labeled_transactions = db.scalar(
        select(func.count(Transaction.id)).where(Transaction.label_known.is_(True))
    ) or 0
    fraud = db.scalar(
        select(func.count(Transaction.id)).where(
            Transaction.label_known.is_(True),
            Transaction.is_fraud.is_(True),
        )
    ) or 0
    high_risk = db.scalar(
        select(func.count(RiskAssessment.id)).where(RiskAssessment.risk_level == "high")
    ) or 0
    open_alerts = db.scalar(select(func.count(Alert.id)).where(Alert.status == "open")) or 0
    activity = db.execute(
        select(Transaction.step, func.count(Transaction.id), func.sum(Transaction.amount))
        .where(Transaction.step.is_not(None))
        .group_by(Transaction.step)
        .order_by(Transaction.step.desc())
        .limit(14)
    ).all()
    distribution = db.execute(
        select(RiskAssessment.risk_level, func.count(RiskAssessment.id))
        .group_by(RiskAssessment.risk_level)
    ).all()
    return {
        "total_transactions": total,
        "total_amount": round(amount, 2),
        "fraud_transactions": fraud,
        "fraud_labeled_transactions": labeled_transactions,
        "fraud_rate": round(fraud / labeled_transactions, 6) if labeled_transactions else 0.0,
        "high_risk_transactions": high_risk,
        "open_alerts": open_alerts,
        "activity": [
            {"step": step, "count": count, "amount": round(total_amount or 0, 2)}
            for step, count, total_amount in reversed(activity)
        ],
        "risk_distribution": [
            {"risk_level": level, "count": count} for level, count in distribution
        ],
    }
