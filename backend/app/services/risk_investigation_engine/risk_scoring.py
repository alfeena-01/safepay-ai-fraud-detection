
import math


# Risk score calculation weights
RISK_WEIGHTS = {
    "fraud_probability": 35,
    "anomaly_score": 25,
    "behaviour_deviation": 20,
    "graph_risk": 20,
}


def classify_risk_level(risk_score):
    """
    Classify a transaction based on its risk score.
    """

    if not 0 <= risk_score <= 100:
        raise ValueError("Risk score must be between 0 and 100")

    if risk_score < 30:
        return "Low"
    elif risk_score < 60:
        return "Medium"
    elif risk_score < 80:
        return "High"
    else:
        return "Critical"


def calculate_transaction_risk(
    transaction_id,
    fraud_probability=None,
    anomaly_score=None,
    behaviour_deviation=None,
    graph_risk=None,
    rule_evidence=None,
):
    """
    Calculate the overall transaction risk score.

    All available scores must be between 0 and 1.
    Missing signals are excluded and remaining weights
    are proportionally adjusted.
    """

    components = {
        "fraud_probability": fraud_probability,
        "anomaly_score": anomaly_score,
        "behaviour_deviation": behaviour_deviation,
        "graph_risk": graph_risk,
    }

    available_components = {}
    unavailable_components = []

    for name, value in components.items():

        if value is None:
            unavailable_components.append(name)
            continue

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number or None")

        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1")

        available_components[name] = value

    if not available_components:
        raise ValueError("At least one risk signal is required")

    # Calculate using only available signals
    total_weight = sum(
        RISK_WEIGHTS[name] for name in available_components
    )

    weighted_score = sum(
        value * RISK_WEIGHTS[name]
        for name, value in available_components.items()
    )

    risk_score = round((weighted_score / total_weight) * 100)

    risk_level = classify_risk_level(risk_score)

    reasons = generate_risk_reasons(
        available_components,
        rule_evidence
    )

    return {
        "transaction_id": transaction_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_components": components,
        "unavailable_components": unavailable_components,
        "reasons": reasons,
        "recommended_action": get_recommended_action(risk_level),
    }


def generate_risk_reasons(components, rule_evidence=None):
    """
    Generate explanations for suspicious transaction signals.
    """

    reasons = []

    if components.get("fraud_probability", 0) >= 0.7:
        reasons.append("High fraud model score")

    if components.get("anomaly_score", 0) >= 0.7:
        reasons.append("Unusual transaction pattern")

    if components.get("behaviour_deviation", 0) >= 0.7:
        reasons.append("High account behaviour deviation")

    if components.get("graph_risk", 0) >= 0.7:
        reasons.append("Suspicious connected accounts")

    if rule_evidence:
        reasons.extend(rule_evidence)

    if not reasons:
        reasons.append("No high-risk signals identified")

    return list(dict.fromkeys(reasons))


def get_recommended_action(risk_level):
    """
    Recommend an investigation action based on risk level.
    """

    actions = {
        "Low": "Routine monitoring",
        "Medium": "Further transaction review",
        "High": "Detailed investigator review",
        "Critical": "Priority investigator review",
    }

    return actions[risk_level]
