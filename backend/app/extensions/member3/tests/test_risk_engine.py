from app.detectors.real_time_risk_engine import calculate_risk_score


def test_low_risk():
    result = calculate_risk_score()

    assert result["risk_score"] == 0
    assert result["risk_level"] == "Low Risk"


def test_high_risk():
    result = calculate_risk_score(
        phishing_risk=100,
        account_takeover_risk=100,
        suspicious_login_risk=100,
        duplicate_transaction_risk=100,
        fraud_pattern_risk=100,
        device_fingerprint_risk=100
    )

    assert result["risk_score"] == 100
    assert result["risk_level"] == "High Risk"


def test_medium_risk():
    result = calculate_risk_score(
        phishing_risk=50,
        account_takeover_risk=50,
        suspicious_login_risk=50,
        duplicate_transaction_risk=50,
        fraud_pattern_risk=50,
        device_fingerprint_risk=50
    )

    assert result["risk_score"] == 50
    assert result["risk_level"] == "Medium Risk"


def test_invalid_score():
    try:
        calculate_risk_score(phishing_risk=120)
    except ValueError:
        return

    raise AssertionError("Invalid score was not rejected")


if __name__ == "__main__":
    test_low_risk()
    test_high_risk()
    test_medium_risk()
    test_invalid_score()

    print("ALL RISK ENGINE TESTS PASSED!")