def calculate_risk_score(
    phishing_risk=0,
    account_takeover_risk=0,
    suspicious_login_risk=0,
    duplicate_transaction_risk=0,
    fraud_pattern_risk=0,
    device_fingerprint_risk=0
):
    components = {
        "phishing": phishing_risk,
        "account_takeover": account_takeover_risk,
        "suspicious_login": suspicious_login_risk,
        "duplicate_transaction": duplicate_transaction_risk,
        "fraud_pattern": fraud_pattern_risk,
        "device_fingerprinting": device_fingerprint_risk
    }

    for name, score in components.items():
        if not isinstance(score, (int, float)):
            raise ValueError(f"{name} score must be numeric")

        if not 0 <= score <= 100:
            raise ValueError(f"{name} score must be between 0 and 100")

    risk_score = (
        phishing_risk * 0.20 +
        account_takeover_risk * 0.20 +
        suspicious_login_risk * 0.20 +
        duplicate_transaction_risk * 0.15 +
        fraud_pattern_risk * 0.15 +
        device_fingerprint_risk * 0.10
    )

    risk_score = round(risk_score)

    if risk_score >= 70:
        risk_level = "High Risk"
        action = "Flag for investigation"
    elif risk_score >= 40:
        risk_level = "Medium Risk"
        action = "Further review recommended"
    else:
        risk_level = "Low Risk"
        action = "Normal monitoring"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "recommended_action": action,
        "risk_components": components
    }


if __name__ == "__main__":
    result = calculate_risk_score(
        phishing_risk=75,
        account_takeover_risk=85,
        suspicious_login_risk=100,
        duplicate_transaction_risk=100,
        fraud_pattern_risk=70,
        device_fingerprint_risk=60
    )

    print("\n===== REAL-TIME RISK ANALYSIS =====")
    print("Risk Score:", result["risk_score"])
    print("Risk Level:", result["risk_level"])
    print("Recommended Action:", result["recommended_action"])
    print("Risk Components:", result["risk_components"])