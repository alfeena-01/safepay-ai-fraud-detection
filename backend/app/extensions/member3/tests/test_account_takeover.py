from app.detectors.account_takeover_detector import (
    detect_account_takeover
)


def test_normal_account():
    result = detect_account_takeover()
    assert result["risk_score"] == 0
    assert result["status"] == "Low Risk"


def test_suspicious_account():
    result = detect_account_takeover(
        failed_login_attempts=6,
        new_device=True,
        password_reset_attempts=3,
        unusual_location=True
    )

    assert result["risk_score"] == 85
    assert result["status"] == "High Risk"


def test_new_device():
    result = detect_account_takeover(new_device=True)

    assert result["risk_score"] == 20
    assert result["status"] == "Low Risk"


if __name__ == "__main__":
    test_normal_account()
    test_suspicious_account()
    test_new_device()

    print("ALL ACCOUNT TAKEOVER TESTS PASSED!")