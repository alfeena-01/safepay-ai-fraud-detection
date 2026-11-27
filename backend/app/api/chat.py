from __future__ import annotations

import os
import re
import urllib.error
from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.database.models import RiskAssessment, Transaction
from app.services.chatbot_engine import (
    ChatRequest, ChatResponse, _requested_ids, _transaction_id,
    ask_ollama, local_answer,
)

router = APIRouter(prefix="/chat", tags=["SafePay AI Assistant"])
CHATBOT_PROVIDER = os.getenv("CHATBOT_PROVIDER", "rules").lower()

def _record_context(tx: Transaction, db: Session) -> dict:
    risk = db.scalar(select(RiskAssessment).where(RiskAssessment.transaction_id == tx.id))
    related = db.scalars(
        select(Transaction).where(
            or_(Transaction.name_orig == tx.name_orig, Transaction.name_dest == tx.name_orig,
                Transaction.name_orig == tx.name_dest, Transaction.name_dest == tx.name_dest)
        ).limit(100)
    ).all()
    connected = sorted({
        account for row in related for account in (row.name_orig, row.name_dest)
        if account and account not in {tx.name_orig, tx.name_dest}
    })
    context = {
        "transaction_id": tx.transaction_id, "transaction_type": tx.transaction_type,
        "amount": tx.amount, "sender_account": tx.name_orig, "receiver_account": tx.name_dest,
        "transaction_step": tx.step, "timestamp": tx.created_at.isoformat() if tx.created_at else None,
        "ground_truth_status": (
            "fraud" if tx.label_known and tx.is_fraud
            else "legitimate" if tx.label_known
            else "unknown"
        ),
        "evidence": (
            [f"Ground-truth dataset label is {'fraud' if tx.is_fraud else 'legitimate'}"]
            if tx.label_known
            else []
        ),
        "confirmed_evidence": [], "connected_accounts": connected,
    }
    if risk:
        context.update({
            "risk_score": risk.overall_risk_score, "risk_level": risk.risk_level,
            "fraud_probability": risk.fraud_probability, "anomaly_score": risk.anomaly_score,
            "model_classification": risk.model_classification,
            "classification_threshold": risk.classification_threshold,
            "anomaly_status": risk.anomaly_status,
            "behavior_status": risk.behavior_status,
            "behavior_findings": risk.behavior_findings,
            "graph_risk": risk.graph_risk, "reasons": risk.explanation,
            "recommended_action": risk.recommended_action,
        })
    return context

@router.get("/health")
def chat_health():
    return {"status": "ok", "provider": CHATBOT_PROVIDER}

@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    context = request.transaction_context
    comparisons = request.comparison_context
    requested = _requested_ids(request.message)
    if requested:
        resolved = []
        for transaction_id in requested:
            tx = db.scalar(select(Transaction).options(joinedload(Transaction.risk_assessment)).where(Transaction.transaction_id == transaction_id))
            if tx is None:
                return ChatResponse(reply=f"I couldn't find transaction {transaction_id} in the SafePay database. Check the ID and try again.", provider="database-lookup", used_transaction_context=False)
            resolved.append(_record_context(tx, db))
        context = resolved[0]
        if len(resolved) > 1:
            comparisons = resolved[:2]
    if CHATBOT_PROVIDER == "ollama":
        try:
            reply = ask_ollama(request.message, request.history, context, comparisons)
            if reply:
                return ChatResponse(reply=reply, provider="ollama", used_transaction_context=bool(context or comparisons))
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
            pass
    return ChatResponse(
        reply=local_answer(request.message, context, comparisons),
        provider="safe-fallback", used_transaction_context=bool(context or comparisons),
    )
