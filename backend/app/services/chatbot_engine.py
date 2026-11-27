from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "SafePay AI Assistant"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
CHATBOT_PROVIDER = os.getenv("CHATBOT_PROVIDER", "ollama").lower()

app = FastAPI(title=APP_NAME, version="1.0.0", description="SafePay project assistant chatbot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """You are SafePay AI Assistant, a careful assistant inside a financial fraud detection and investigation prototype.
Help authorised users understand transaction risk, fraud probability, anomaly scores, account-network findings, alerts, investigation cases, reports, and how to use SafePay.
Rules:
- Sound warm, clear, and human. Use everyday language, short sentences, and answer the question first.
- Keep most answers to a few short sentences or 3 brief bullets. Avoid formal reports, jargon, repeated caveats, and long checklists unless the user asks for a full summary.
- Never invent transaction facts, account connections, scores, model outputs, or database records.
- Use only transaction context supplied in the current request. If it is missing, ask the user to open/select a transaction or provide its details.
- Clearly separate transaction facts supplied by SafePay, evidence supplied for review, model predictions/explanations, and your suggested next steps.
- Do not describe a model reason or score as confirmed evidence. Treat evidence records as supplied information, not independently verified facts.
- When asked to compare transactions, compare only the two supplied records and say when a field is missing from either record.
- A high risk score is an indicator for review, not proof of fraud. Never declare a person or transaction guilty.
- Do not recommend automatically freezing, blocking, or transferring money. Recommend review by an authorised investigator.
- Explain technical terms in simple language and give practical next steps.
- Do not request passwords, OTPs, PINs, card numbers, or full bank credentials.
- Make it clear that SafePay is a decision-support prototype, not a real banking service.
"""

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=12)
    transaction_context: dict[str, Any] | None = None
    comparison_context: list[dict[str, Any]] = Field(default_factory=list, max_length=2)

class ChatResponse(BaseModel):
    reply: str
    provider: str
    used_transaction_context: bool


def safe_context(context: dict[str, Any] | None, comparisons: list[dict[str, Any]] | None = None) -> str:
    # Keep the context small and remove likely secrets.
    allowed = {
        "transaction_id", "transaction_type", "amount", "sender_account", "receiver_account",
        "risk_score", "risk_level", "fraud_probability", "anomaly_score", "graph_risk",
        "reasons", "recommended_action", "anomaly_detected", "connected_accounts",
        "suspicious_path_detected", "evidence", "confirmed_evidence", "transaction_step",
        "status", "timestamp", "currency", "investigator_notes", "alert_details", "case_id"
    }
    def clean(record: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in record.items() if k in allowed}

    return json.dumps({
        "selected_transaction": clean(context) if context else None,
        "comparison_transactions": [clean(item) for item in (comparisons or [])],
    }, ensure_ascii=False, default=str)[:9000]


def _transaction_id(record: dict[str, Any]) -> str | None:
    value = record.get("transaction_id")
    return str(value) if value is not None else None


def _display(value: Any) -> str:
    if value is None:
        return "not provided"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _available_records(context: dict[str, Any] | None, comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return ([context] if context else []) + comparisons


def _requested_ids(message: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\b(?:TXN|TX)[-_]?[A-Za-z0-9][A-Za-z0-9_-]*\b", message, flags=re.IGNORECASE)))


def _context_for_question(
    message: str,
    context: dict[str, Any] | None,
    comparisons: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, str | None]:
    records = _available_records(context, comparisons)
    requested_ids = _requested_ids(message)
    for requested_id in requested_ids:
        match = next(
            (record for record in records
             if (_transaction_id(record) or "").casefold() == requested_id.casefold()),
            None
        )
        if match is None:
            return None, (
                f"I don't have transaction data for {requested_id}. Select that transaction in SafePay "
                "or connect the chatbot to the transaction lookup API before asking for its investigation."
            )
    if requested_ids:
        return next(
            record for record in records
            if (_transaction_id(record) or "").casefold() == requested_ids[0].casefold()
        ), None
    return context, None


def _evidence_summary(context: dict[str, Any]) -> str:
    confirmed = context.get("confirmed_evidence")
    supplied = context.get("evidence")
    if confirmed:
        return f"The supplied record marks this evidence as confirmed: {_display(confirmed)}"
    if supplied:
        return f"Evidence to check (provided with the record, not independently verified): {_display(supplied)}"
    return "No evidence details were included with this transaction."


def _prediction_summary(context: dict[str, Any]) -> str:
    fields = [
        ("Risk level", context.get("risk_level")),
        ("Risk score", context.get("risk_score")),
        ("Fraud probability", context.get("fraud_probability")),
        ("Anomaly score", context.get("anomaly_score")),
        ("Graph risk", context.get("graph_risk")),
        ("Why the model flagged it", context.get("reasons")),
    ]
    return "\n".join(f"- {label}: {_display(value)}" for label, value in fields if value is not None)


def _next_steps(context: dict[str, Any]) -> str:
    steps = [
        "Check the transaction details and supporting evidence.",
        "Compare this activity with the account's usual behaviour.",
        "Review any linked accounts, then record what you find.",
    ]
    recommendation = context.get("recommended_action")
    if recommendation:
        steps = [f"The system suggests: {_display(recommendation)}", *steps[:2]]
    return "\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))


def _compare_transactions(records: list[dict[str, Any]]) -> str:
    if len(records) < 2:
        return (
            "I can compare two transactions, but only one transaction record is available. "
            "Select or provide a second transaction record; I won't infer its details."
        )
    first, second = records[:2]
    fields = (
        ("Transaction ID", "transaction_id"),
        ("Type", "transaction_type"),
        ("Amount", "amount"),
        ("Risk level", "risk_level"),
        ("Risk score", "risk_score"),
        ("Fraud probability", "fraud_probability"),
        ("Anomaly score", "anomaly_score"),
        ("Connected accounts", "connected_accounts"),
        ("Model explanations/reasons", "reasons"),
    )
    lines = ["Here is a side-by-side comparison of the records you provided:"]
    for label, key in fields:
        left, right = first.get(key), second.get(key)
        if left is not None or right is not None:
            lines.append(f"- {label}: {_display(left)} | {_display(right)}")
    lines.extend([
        "",
        "Scores and model reasons are AI estimates, not proof of fraud. Review the evidence for each transaction."
    ])
    return "\n".join(lines)


def local_answer(
    message: str,
    context: dict[str, Any] | None,
    comparisons: list[dict[str, Any]] | None = None
) -> str:
    q = message.lower()
    comparisons = comparisons or []
    records = _available_records(context, comparisons)

    if re.search(r"\b(compare|comparison|versus|vs\.?)\b", q):
        return _compare_transactions(records)

    ctx, missing_id_reply = _context_for_question(message, context, comparisons)
    if missing_id_reply:
        return missing_id_reply
    ctx = ctx or {}
    tid = _transaction_id(ctx)
    heading = f"Transaction {tid}" if tid else "Selected transaction"

    if re.search(r"\b(hello|hi|hey|good morning)\b", q):
        return "Hi! I can help you understand a transaction, its risk signals, and what to check next. What would you like to look at?"
    if any(term in q for term in ("summar", "overview", "case summary", "investigation summary")):
        if not ctx:
            return "Choose a transaction first, and I can give you a quick summary."
        amount = _display(ctx.get("amount"))
        currency = ctx.get("currency")
        if amount != "not provided" and currency:
            amount = f"{amount} {currency}"
        facts = [
            f"- Transaction data supplied by SafePay: {heading}; type {_display(ctx.get('transaction_type'))}; amount {amount}."
        ]
        if ctx.get("sender_account") is not None or ctx.get("receiver_account") is not None:
            facts.append(
                f"- Accounts supplied: sender {_display(ctx.get('sender_account'))}; "
                f"receiver {_display(ctx.get('receiver_account'))}."
            )
        predictions = _prediction_summary(ctx)
        return "\n".join([
            f"Quick summary: {heading}",
            *facts,
            "",
            "Evidence:",
            f"- {_evidence_summary(ctx)}",
            "",
            "AI estimates:",
            predictions or "- No AI results were included.",
            "",
            "What to check next:",
            _next_steps(ctx),
            "",
            "The AI can flag activity for review, but it can't confirm fraud."
        ])
    if any(term in q for term in ("next", "what should", "examine", "recommend", "investigator")) and ctx:
        return f"For {heading}, I would start here:\n{_next_steps(ctx)}\n\nThese are suggestions, not confirmed findings."
    if any(term in q for term in ("connected", "network", "account path", "account(s)")):
        if not ctx:
            return "Choose a transaction with network results, and I can show its linked accounts."
        connected = ctx.get("connected_accounts")
        if connected is None and not ctx.get("sender_account") and not ctx.get("receiver_account"):
            return f"I don't see any account-link details for {heading}, so I can't list connected accounts yet."
        accounts = []
        if ctx.get("sender_account") is not None:
            accounts.append(f"Sender: {_display(ctx['sender_account'])}")
        if ctx.get("receiver_account") is not None:
            accounts.append(f"Receiver: {_display(ctx['receiver_account'])}")
        if connected is not None:
            accounts.append(f"Connected accounts from supplied analysis: {_display(connected)}")
        if ctx.get("suspicious_path_detected") is not None:
            accounts.append(f"Suspicious path flag from supplied analysis: {_display(ctx['suspicious_path_detected'])}")
        return (
            f"Here is what I can see for {heading}:\n" + "\n".join(f"- {item}" for item in accounts) +
            "\n\nA link by itself doesn't mean anything is wrong. Check it in context."
        )
    if any(term in q for term in ("pattern", "anomaly", "unusual", "flagged", "risk", "score", "fraud", "suspicious")):
        if not ctx:
            return "Choose a transaction first so I can explain its actual risk signals. I don't want to guess."
        predictions = _prediction_summary(ctx)
        return "\n".join([
            f"Here is why {tid or 'this transaction'} was flagged:",
            "AI estimates:",
            predictions or "- No AI scores or reasons were included.",
            "",
            "Evidence:",
            f"- {_evidence_summary(ctx)}",
            "",
            "What to check:",
            _next_steps(ctx),
            "",
            "These AI signals are a reason to take a closer look, not proof of fraud."
        ])
    if any(term in q for term in ("alert", "notification")):
        return "An alert means a transaction may need a closer look. Check its details and history; the alert itself doesn't confirm fraud."
    if any(term in q for term in ("case", "investigation", "investigate")):
        return "Open the transaction and check its evidence and AI results. If it needs more review, add it to a case and note what you find. AI scores aren't final decisions."
    if any(term in q for term in ("report", "pdf", "export")):
        return "A useful report includes the transaction, AI results, evidence, your notes, and what happens next. Double-check the details before exporting."
    if any(term in q for term in ("dashboard", "how do i use", "how to use", "features")):
        return "Use Transaction Monitoring to find activity, Risk Analysis to review a transaction, Account Network to see links, and Cases or Reports to track your investigation."
    if any(term in q for term in ("what is fraud", "define fraud", "what does fraud mean")):
        return "Fraud is using deception to gain money or another benefit. SafePay can flag activity to review, but a flag doesn't prove fraud happened."
    if ctx:
        return (
            f"I have the details for {heading}. I can explain its risk signals, show linked accounts, summarise it, or help you decide what to check next."
        )
    return "Choose a transaction in SafePay and I can explain its risk signals, compare records, or suggest what to check next. I only use details provided to me."


def ask_ollama(
    message: str,
    history: list[dict[str, str]],
    context: dict[str, Any] | None,
    comparisons: list[dict[str, Any]] | None = None
) -> str:
    messages: list[dict[str, str]] = [{
        "role": "system",
        "content": SYSTEM_PROMPT + "\nTransaction records supplied with this request (JSON): "
        + safe_context(context, comparisons)
    }]
    for item in history[-10:]:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            messages.append({"role": role, "content": content[:3000]})
    messages.append({"role": "user", "content": message})
    payload = json.dumps({"model": OLLAMA_MODEL, "messages": messages, "stream": False}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result.get("message", {}).get("content", "").strip()

@app.get("/api/health")
def health():
    return {"status": "ok", "service": APP_NAME, "provider": CHATBOT_PROVIDER, "model": OLLAMA_MODEL if CHATBOT_PROVIDER == "ollama" else "local-rules"}

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    records = _available_records(request.transaction_context, request.comparison_context)
    for requested_id in _requested_ids(request.message):
        if not any((_transaction_id(record) or "").casefold() == requested_id.casefold() for record in records):
            return ChatResponse(
                reply=(
                    f"I don't have transaction data for {requested_id}. Select that transaction in SafePay "
                    "or connect the chatbot to the transaction lookup API before asking for its investigation."
                ),
                provider="safe-context",
                used_transaction_context=False,
            )
    if CHATBOT_PROVIDER == "ollama":
        try:
            reply = ask_ollama(
                request.message,
                request.history,
                request.transaction_context,
                request.comparison_context
            )
            if reply:
                return ChatResponse(reply=reply, provider=f"ollama:{OLLAMA_MODEL}", used_transaction_context=bool(records))
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
            pass
    return ChatResponse(
        reply=local_answer(request.message, request.transaction_context, request.comparison_context),
        provider="safe-fallback",
        used_transaction_context=bool(records),
    )
