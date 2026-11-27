def detect_account_takeover(
    failed_login_attempts=0,
    new_device=False,
    password_reset_attempts=0,
    profile_changed=False,
    unusual_location=False
):
    risk_score = 0
    reasons = []

    # Failed login attempts
    if failed_login_attempts >= 5:
        risk_score += 25
        reasons.append("Multiple failed login attempts")

    # New device
    if new_device:
        risk_score += 20
        reasons.append("Login from a new device")

    # Password reset attempts
    if password_reset_attempts >= 3:
        risk_score += 20
        reasons.append("Multiple password reset attempts")

    # Profile changes
    if profile_changed:
        risk_score += 15
        reasons.append("Account profile recently changed")

    # Unusual location
    if unusual_location:
        risk_score += 20
        reasons.append("Login from an unusual location")

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
    result = detect_account_takeover(
        failed_login_attempts=6,
        new_device=True,
        password_reset_attempts=3,
        profile_changed=False,
        unusual_location=True
    )

    print("\n===== ACCOUNT TAKEOVER ANALYSIS =====")
    print("Risk Score:", result["risk_score"])
    print("Status:", result["status"])
    print("Reasons:", result["reasons"])