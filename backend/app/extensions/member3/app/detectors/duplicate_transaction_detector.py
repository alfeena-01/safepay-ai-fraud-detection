def detect_duplicate_transaction(transaction, previous_transactions):
    duplicate = False
    reasons = []

    fields_to_compare = [
        "account_id",
        "amount",
        "merchant",
        "timestamp"
    ]

    for previous in previous_transactions:
        if all(
            transaction.get(field) == previous.get(field)
            for field in fields_to_compare
        ):
            duplicate = True
            reasons.append("Matching transaction already exists")
            break

    return {
        "is_duplicate": duplicate,
        "status": "Duplicate" if duplicate else "Unique",
        "reasons": reasons
    }


if __name__ == "__main__":
    current_transaction = {
        "account_id": "ACC001",
        "amount": 5000,
        "merchant": "ABC Store",
        "timestamp": "2026-11-26 10:30:00"
    }

    previous_transactions = [
        {
            "account_id": "ACC001",
            "amount": 5000,
            "merchant": "ABC Store",
            "timestamp": "2026-11-26 10:30:00"
        }
    ]

    result = detect_duplicate_transaction(
        current_transaction,
        previous_transactions
    )

    print("\n===== DUPLICATE TRANSACTION ANALYSIS =====")
    print("Duplicate:", result["is_duplicate"])
    print("Status:", result["status"])
    print("Reasons:", result["reasons"])