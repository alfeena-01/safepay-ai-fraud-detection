from datetime import datetime, timezone


def generate_investigation_report(investigation_result):
    """
    Generate a structured investigation report.
    """

    if not isinstance(investigation_result, dict):
        raise ValueError("Investigation result must be a dictionary")

    required_fields = [
        "transaction_id",
        "risk_score",
        "risk_level",
        "reasons",
    ]

    for field in required_fields:
        if field not in investigation_result:
            raise ValueError(f"Missing required field: {field}")

    report = {
        "report_id": f"RPT-{investigation_result['transaction_id']}",

        "transaction_id": investigation_result["transaction_id"],

        "generated_at": datetime.now(timezone.utc).isoformat(),

        "risk_assessment": {
            "risk_score": investigation_result["risk_score"],
            "risk_level": investigation_result["risk_level"],
            "fraud_probability": investigation_result.get(
                "fraud_probability"
            ),
            "investigation_priority": investigation_result.get(
                "investigation_priority", "Normal"
            ),
        },

        "investigation_details": {
            "reasons": investigation_result.get("reasons", []),

            "shap_explanations": investigation_result.get(
                "shap_explanations", []
            ),

            "summary": investigation_result.get(
                "investigation_summary", ""
            ),
        },

        "recommended_action": investigation_result.get(
            "recommended_action", "Manual Review"
        ),

        "investigation_status": investigation_result.get(
            "investigation_status", "Pending Review"
        ),
    }

    return report