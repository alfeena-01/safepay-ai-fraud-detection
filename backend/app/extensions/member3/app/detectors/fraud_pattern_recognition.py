def detect_fraud_patterns(transactions):
    patterns = []
    risk_score = 0

    if not transactions:
        return {
            "risk_score": 0,
            "patterns": [],
            "status": "No Data"
        }

    amounts = [t.get("amount", 0) for t in transactions]

    # Pattern 1: High-value transactions
    high_value = [amount for amount in amounts if amount >= 50000]

    if high_value:
        patterns.append("High-value transaction detected")
        risk_score += 30

    # Pattern 2: Repeated transactions
    if len(transactions) >= 3:
        patterns.append("Multiple transactions detected")
        risk_score += 25

    # Pattern 3: Same merchant transactions
    merchants = [t.get("merchant") for t in transactions]

    if len(merchants) != len(set(merchants)):
        patterns.append("Repeated merchant activity detected")
        risk_score += 25

    # Pattern 4: Unusual transaction amount
    if amounts and max(amounts) > 3 * max(min(amounts), 1):
        patterns.append("Unusual transaction amount variation")
        risk_score += 20

    risk_score = min(risk_score, 100)

    if risk_score >= 60:
        status = "High Risk"
    elif risk_score >= 30:
        status = "Potential Risk"
    else:
        status = "Low Risk"

    return {
        "risk_score": risk_score,
        "patterns": patterns,
        "status": status
    }


if __name__ == "__main__":

    sample_transactions = [
        {"amount": 500, "merchant": "ABC Store"},
        {"amount": 600, "merchant": "ABC Store"},
        {"amount": 75000, "merchant": "ABC Store"},
    ]

    result = detect_fraud_patterns(sample_transactions)

    print("\n===== FRAUD PATTERN ANALYSIS =====")
    print("Risk Score:", result["risk_score"])
    print("Status:", result["status"])
    print("Detected Patterns:", result["patterns"])