from app.detectors.phishing_url_detector import detect_phishing_url


def test_normal_url():
    result = detect_phishing_url("https://example.com")
    assert result["status"] == "Low Risk"


def test_suspicious_url():
    result = detect_phishing_url(
        "http://secure-login-verify-example.com"
    )
    assert result["risk_score"] >= 25


def test_ip_url():
    result = detect_phishing_url("http://192.168.1.1")
    assert result["risk_score"] >= 25


if __name__ == "__main__":
    test_normal_url()
    test_suspicious_url()
    test_ip_url()

    print("ALL PHISHING TESTS PASSED!")