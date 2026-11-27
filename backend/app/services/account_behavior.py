from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Transaction

MINIMUM_ACCOUNT_HISTORY = 5
MAXIMUM_BEHAVIOR_SAMPLE = 1000
HIGH_AMOUNT_MULTIPLE = 5.0


def analyze_sender_behavior(
    db: Session,
    account_id: str | None,
    amount: float,
    current_transaction_pk: int | None = None,
) -> dict:
    if not account_id:
        return {
            "status": "unavailable",
            "history_count": 0,
            "median_amount": None,
            "current_to_median_ratio": None,
            "findings": [],
        }

    query = select(Transaction).where(Transaction.name_orig == account_id)
    if current_transaction_pk is not None:
        query = query.where(Transaction.id < current_transaction_pk)
    history = db.scalars(
        query.order_by(Transaction.id.desc()).limit(MAXIMUM_BEHAVIOR_SAMPLE)
    ).all()
    if len(history) < MINIMUM_ACCOUNT_HISTORY:
        return {
            "status": "insufficient_history",
            "history_count": len(history),
            "median_amount": None,
            "current_to_median_ratio": None,
            "findings": [],
        }

    typical_amount = float(median(float(item.amount) for item in history))
    ratio = amount / typical_amount if typical_amount > 0 else None
    findings = []
    if ratio is not None and ratio >= HIGH_AMOUNT_MULTIPLE:
        findings.append(
            f"Outgoing amount is {ratio:.1f} times the sender's median "
            f"across {len(history)} prior transactions."
        )

    return {
        "status": "available",
        "history_count": len(history),
        "median_amount": round(typical_amount, 2),
        "current_to_median_ratio": round(ratio, 2) if ratio is not None else None,
        "findings": findings,
    }


def summarize_account_behavior(db: Session, account_id: str) -> dict:
    outgoing_count, outgoing_total, outgoing_average, outgoing_minimum, outgoing_maximum = (
        db.execute(
            select(
                func.count(Transaction.id),
                func.coalesce(func.sum(Transaction.amount), 0.0),
                func.avg(Transaction.amount),
                func.min(Transaction.amount),
                func.max(Transaction.amount),
            ).where(Transaction.name_orig == account_id)
        ).one()
    )
    incoming_count, incoming_total = db.execute(
        select(
            func.count(Transaction.id),
            func.coalesce(func.sum(Transaction.amount), 0.0),
        ).where(Transaction.name_dest == account_id)
    ).one()
    types = db.execute(
        select(Transaction.transaction_type, func.count(Transaction.id))
        .where(Transaction.name_orig == account_id)
        .group_by(Transaction.transaction_type)
        .order_by(func.count(Transaction.id).desc())
    ).all()
    recent = db.scalars(
        select(Transaction)
        .where((Transaction.name_orig == account_id) | (Transaction.name_dest == account_id))
        .order_by(Transaction.id.desc())
        .limit(20)
    ).all()

    return {
        "account_id": account_id,
        "history_status": "available" if outgoing_count or incoming_count else "no_history",
        "outgoing": {
            "transaction_count": outgoing_count,
            "total_amount": round(float(outgoing_total), 2),
            "average_amount": round(float(outgoing_average), 2) if outgoing_average is not None else None,
            "minimum_amount": float(outgoing_minimum) if outgoing_minimum is not None else None,
            "maximum_amount": float(outgoing_maximum) if outgoing_maximum is not None else None,
            "common_types": [
                {"transaction_type": transaction_type, "count": count}
                for transaction_type, count in types
            ],
        },
        "incoming": {
            "transaction_count": incoming_count,
            "total_amount": round(float(incoming_total), 2),
        },
        "recent_transactions": [
            {
                "transaction_id": item.transaction_id,
                "direction": "outgoing" if item.name_orig == account_id else "incoming",
                "amount": float(item.amount),
                "transaction_type": item.transaction_type,
                "created_at": item.created_at,
            }
            for item in recent
        ],
    }
