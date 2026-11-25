import pandas as pd

from .risk_scoring import calculate_transaction_risk
from .shap_explainer import generate_shap_explanation


def investigate_transaction(
    transaction,
    model=None,
    background_data=None
):
    """
    Investigate a transaction and optionally generate
    SHAP explanations using a trained ML model.
    """

    if not isinstance(transaction, dict):
        raise ValueError("Transaction must be a dictionary")

    transaction_id = transaction.get("transaction_id")

    if not isinstance(transaction_id, str) or not transaction_id.strip():
        raise ValueError("A valid transaction_id is required")

    # Generate SHAP explanation
    shap_result = None

    if model is not None:

        if not isinstance(background_data, pd.DataFrame):
            raise ValueError("Background data must be a DataFrame")

        features = transaction.get("features")

        if not isinstance(features, dict) or not features:
            raise ValueError("Transaction features must be provided")

        transaction_data = pd.DataFrame([features])

        shap_result = generate_shap_explanation(
            model=model,
            background_data=background_data,
            transaction_data=transaction_data
        )

        fraud_probability = shap_result["fraud_probability"]
        shap_explanations = shap_result["feature_explanations"]

    else:
        fraud_probability = transaction.get("fraud_probability")

        shap_explanations = transaction.get(
            "shap_explanations",
            transaction.get("feature_explanations", [])
        )

    # Calculate transaction risk
    risk_result = calculate_transaction_risk(
        transaction_id=transaction_id,
        fraud_probability=fraud_probability,
        anomaly_score=transaction.get("anomaly_score"),
        behaviour_deviation=transaction.get("behaviour_deviation"),
        graph_risk=transaction.get("graph_risk"),
        rule_evidence=transaction.get("rule_evidence"),
    )

    # Prepare investigation summary
    reasons = risk_result["reasons"]

    summary = (
        f"Transaction {transaction_id} received a "
        f"{risk_result['risk_level']} risk classification "
        f"with a risk score of {risk_result['risk_score']}/100. "
        f"Findings: {'; '.join(reasons)}."
    )

    # Investigation priority
    priority = {
        "Low": "Routine",
        "Medium": "Normal",
        "High": "High",
        "Critical": "Urgent",
    }

    # Final investigation result
    investigation_result = {
        **risk_result,

        "fraud_probability": fraud_probability,

        "shap_explanations": shap_explanations,

        "shap_base_value": (
            shap_result["base_value"]
            if shap_result is not None else None
        ),

        "investigation_priority": priority[risk_result["risk_level"]],

        "investigation_summary": summary,

        "investigation_status": "Pending Review",
    }

    return investigation_result