from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.database.models import RiskAssessment, Transaction

router = APIRouter(prefix="/accounts", tags=["account network"])


@router.get("/{account_id}/network")
def account_network(account_id: str, db: Session = Depends(get_db)):
    transactions = db.scalars(
        select(Transaction)
        .options(joinedload(Transaction.risk_assessment))
        .where(or_(Transaction.name_orig == account_id, Transaction.name_dest == account_id))
        .order_by(Transaction.id.desc())
        .limit(200)
    ).unique().all()
    related: dict[str, dict] = {}
    edges = []
    for tx in transactions:
        other = tx.name_dest if tx.name_orig == account_id else tx.name_orig
        if not other:
            continue
        suspicious = tx.is_fraud or (
            tx.risk_assessment is not None and tx.risk_assessment.overall_risk_score >= 70
        )
        item = related.setdefault(other, {"account_id": other, "transaction_count": 0, "total_amount": 0.0})
        item["transaction_count"] += 1
        item["total_amount"] += tx.amount
        edges.append({
            "transaction_id": tx.transaction_id,
            "from": tx.name_orig,
            "to": tx.name_dest,
            "amount": tx.amount,
            "suspicious": suspicious,
        })
    return {
        "account_id": account_id,
        "transaction_count": len(transactions),
        "connected_accounts": [
            {**value, "total_amount": round(value["total_amount"], 2)}
            for value in sorted(related.values(), key=lambda row: row["transaction_count"], reverse=True)
        ],
        "suspicious_connections": sum(edge["suspicious"] for edge in edges),
        "edges": edges,
        "truncated": len(transactions) == 200,
    }