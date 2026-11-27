from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.database.models import RiskAssessment, Transaction
from app.services.account_behavior import summarize_account_behavior

router = APIRouter(prefix="/accounts", tags=["account network"])


@router.get("/{account_id}/behavior")
def account_behavior(account_id: str, db: Session = Depends(get_db)):
    """Return observed transaction history without treating a new account as suspicious."""
    return summarize_account_behavior(db, account_id)


@router.get("/{account_id}/network")
def account_network(account_id: str, depth: int = 1, db: Session = Depends(get_db)):
    """Explore direct (depth=1) or multi-hop (depth=2..3) account relationships."""
    depth = max(1, min(int(depth), 3))
    visited = {account_id}
    frontier = {account_id}
    nodes: dict[str, dict] = {}
    edge_map: dict[str, dict] = {}
    truncated = False

    for level in range(1, depth + 1):
        if not frontier:
            break
        batch = db.scalars(
            select(Transaction)
            .options(joinedload(Transaction.risk_assessment))
            .where(or_(Transaction.name_orig.in_(frontier), Transaction.name_dest.in_(frontier)))
            .order_by(Transaction.id.desc())
            .limit(500)
        ).unique().all()
        if len(batch) >= 500:
            truncated = True
        next_frontier: set[str] = set()
        for tx in batch:
            source, target = tx.name_orig, tx.name_dest
            if not source or not target:
                continue
            suspicious = bool(
                (tx.label_known and tx.is_fraud)
                or (tx.risk_assessment and tx.risk_assessment.overall_risk_score >= 70)
            )
            edge_key = f"{tx.transaction_id}:{source}:{target}"
            if edge_key in edge_map:
                edge_map[edge_key]["depth"] = min(edge_map[edge_key]["depth"], level)
                continue
            edge_map[edge_key] = {
                "transaction_id": tx.transaction_id, "from": source, "to": target,
                "amount": tx.amount, "suspicious": suspicious, "depth": level,
            }
            for account in (source, target):
                if account == account_id:
                    continue
                node = nodes.setdefault(account, {"account_id": account, "transaction_count": 0,
                                                  "total_amount": 0.0, "depth": level,
                                                  "suspicious_transactions": 0})
                node["transaction_count"] += 1
                node["total_amount"] += float(tx.amount or 0)
                node["suspicious_transactions"] += int(suspicious)
                node["depth"] = min(node["depth"], level)
                if account not in visited:
                    next_frontier.add(account)
        visited.update(frontier)
        frontier = next_frontier - visited

    edges = list(edge_map.values())
    return {
        "account_id": account_id,
        "depth": depth,
        "transaction_count": len(edges),
        "connected_accounts": [
            {**value, "total_amount": round(value["total_amount"], 2)}
            for value in sorted(nodes.values(), key=lambda row: (row["depth"], -row["transaction_count"]))
        ],
        "suspicious_connections": sum(edge["suspicious"] for edge in edges),
        "edges": edges,
        "truncated": truncated,
        "disclaimer": "A shared transaction path is a relationship signal, not proof of coordinated fraud.",
    }
