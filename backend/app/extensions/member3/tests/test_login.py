from app.detectors.suspicious_login_detector import (
    detect_suspicious_login
)


def test_normal_login():
    result = detect_suspicious_login()

    assert result["risk_score"] == 0
    assert result["status"] == "Low Risk"


def test_suspicious_login():
    result = detect_suspicious_login(
        new_device=True,
        unusual_time=True,
        unusual_location=True,
        failed_attempts=3
    )

    assert result["risk_score"] == 100
    assert result["status"] == "High Risk"


def test_new_device():
    result = detect_suspicious_login(new_device=True)

    assert result["risk_score"] == 25
    assert result["status"] == "Low Risk"


if __name__ == "__main__":
    test_normal_login()
    test_suspicious_login()
    test_new_device()

    print("ALL SUSPICIOUS LOGIN TESTS PASSED!")