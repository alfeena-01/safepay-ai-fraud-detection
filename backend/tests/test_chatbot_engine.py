from app.services.chatbot_engine import local_answer


def test_chatbot_does_not_invent_transaction_records():
    answer = local_answer("Explain TXN-NOT-LOADED risk", None)
    assert "Choose a transaction" in answer or "don't have transaction data" in answer.lower()


def test_chatbot_explains_supplied_risk_as_estimate():
    answer = local_answer(
        "Why is this transaction suspicious?",
        {
            "transaction_id": "TXN-TEST-1",
            "risk_level": "high",
            "risk_score": 82,
            "reasons": ["Unusual transaction pattern"],
            "evidence": [],
        },
    )
    assert "82" in answer
    assert "not proof of fraud" in answer.lower()


def test_chatbot_uses_actual_comparison_records_only():
    answer = local_answer(
        "Compare these transactions",
        {"transaction_id": "TXN-A", "amount": 10},
        [{"transaction_id": "TXN-B", "amount": 20}],
    )
    assert "TXN-A" in answer and "TXN-B" in answer
    assert "10" in answer and "20" in answer
