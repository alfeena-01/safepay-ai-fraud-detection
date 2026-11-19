from app.database.models import Transaction


MODEL_VERSION = "demo-heuristic-v1"


def assess_transaction(transaction: Transaction) -> dict[str, float | str]:
    """Return a transparent placeholder score until a trained model is integrated."""
    amount_score = min(transaction.amount / 100_000, 1.0)
    type_score = 0.9 if transaction.transaction_type.upper() in {"TRANSFER", "CASH_OUT"} else 0.2
    balance_score = 0.8 if (
        transaction.old_balance_org is not None
        and transaction.new_balance_orig is not None
        and transaction.old_balance_org > 0
        and transaction.new_balance_orig == 0
    ) else 0.15
    graph_risk = 0.6 if transaction.name_orig and transaction.name_orig == transaction.name_dest else 0.1
    probability = min(0.65 * type_score + 0.25 * amount_score + 0.1 * balance_score, 1.0)
    overall = round((probability * 0.5 + amount_score * 0.2 + balance_score * 0.15 + graph_risk * 0.15) * 100, 1)
    level = "high" if overall >= 70 else "medium" if overall >= 40 else "low"
    explanation = (
        "Demo heuristic: score combines transaction type, amount, balance movement, and a basic account-link check. "
        "This is not a trained or calibrated fraud model."
    )
    action = (
        "Escalate for analyst review" if level == "high"
        else "Review supporting context" if level == "medium"
        else "Continue routine monitoring"
    )
    return {
        "fraud_probability": round(probability, 4),
        "anomaly_score": round(amount_score, 4),
        "graph_risk": round(graph_risk, 4),
        "overall_risk_score": overall,
        "risk_level": level,
        "explanation": explanation,
        "recommended_action": action,
        "model_version": MODEL_VERSION,
    }
