from app.detectors.duplicate_transaction_detector import (
    detect_duplicate_transaction
)


def test_duplicate_transaction():
    current = {
        "account_id": "ACC001",
        "amount": 5000,
        "merchant": "ABC Store",
        "timestamp": "2026-11-26 10:30:00"
    }

    previous = [current.copy()]

    result = detect_duplicate_transaction(current, previous)

    assert result["is_duplicate"] is True
    assert result["status"] == "Duplicate"


def test_unique_transaction():
    current = {
        "account_id": "ACC002",
        "amount": 1000,
        "merchant": "XYZ Store",
        "timestamp": "2026-11-26 11:00:00"
    }

    previous = [
        {
            "account_id": "ACC001",
            "amount": 5000,
            "merchant": "ABC Store",
            "timestamp": "2026-11-26 10:30:00"
        }
    ]

    result = detect_duplicate_transaction(current, previous)

    assert result["is_duplicate"] is False
    assert result["status"] == "Unique"


if __name__ == "__main__":
    test_duplicate_transaction()
    test_unique_transaction()

    print("ALL DUPLICATE TRANSACTION TESTS PASSED!")