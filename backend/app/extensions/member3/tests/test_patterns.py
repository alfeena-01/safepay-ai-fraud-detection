from app.detectors.fraud_pattern_recognition import detect_fraud_patterns


def test_no_data():
    result = detect_fraud_patterns([])
    assert result["risk_score"] == 0
    assert result["status"] == "No Data"


def test_high_value():
    transactions = [
        {"amount": 75000, "merchant": "ABC Store"}
    ]
    result = detect_fraud_patterns(transactions)
    assert "High-value transaction detected" in result["patterns"]


def test_repeated_transactions():
    transactions = [
        {"amount": 500, "merchant": "ABC"},
        {"amount": 600, "merchant": "ABC"},
        {"amount": 700, "merchant": "ABC"}
    ]
    result = detect_fraud_patterns(transactions)
    assert "Multiple transactions detected" in result["patterns"]


def test_repeated_merchant():
    transactions = [
        {"amount": 500, "merchant": "ABC"},
        {"amount": 600, "merchant": "ABC"}
    ]
    result = detect_fraud_patterns(transactions)
    assert "Repeated merchant activity detected" in result["patterns"]


if __name__ == "__main__":
    test_no_data()
    test_high_value()
    test_repeated_transactions()
    test_repeated_merchant()

    print("ALL FRAUD PATTERN TESTS PASSED!")