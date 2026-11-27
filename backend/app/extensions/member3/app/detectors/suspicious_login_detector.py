def detect_suspicious_login(
    new_device=False,
    unusual_time=False,
    unusual_location=False,
    failed_attempts=0
):
    risk_score = 0
    reasons = []

    if new_device:
        risk_score += 25
        reasons.append("Login from a new device")

    if unusual_time:
        risk_score += 20
        reasons.append("Login at an unusual time")

    if unusual_location:
        risk_score += 30
        reasons.append("Login from an unusual location")

    if failed_attempts >= 3:
        risk_score += 25
        reasons.append("Multiple failed login attempts")

    risk_score = min(risk_score, 100)

    if risk_score >= 60:
        status = "High Risk"
    elif risk_score >= 30:
        status = "Potential Risk"
    else:
        status = "Low Risk"

    return {
        "risk_score": risk_score,
        "status": status,
        "reasons": reasons
    }


if __name__ == "__main__":
    result = detect_suspicious_login(
        new_device=True,
        unusual_time=True,
        unusual_location=True,
        failed_attempts=3
    )

    print("\n===== SUSPICIOUS LOGIN ANALYSIS =====")
    print("Risk Score:", result["risk_score"])
    print("Status:", result["status"])
    print("Reasons:", result["reasons"])