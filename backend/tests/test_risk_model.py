from array import array

from app.database.models import Transaction
from app.services.anomaly_detection_engine.model import (
    FEATURE_NAMES,
    assess_transaction,
    build_feature_vector,
    transaction_features,
)
from ml.train_explainable import REQUIRED_COLUMNS, evaluate


def test_model_and_api_encode_the_same_transaction_features():
    row = {
        "step": 3,
        "type": "TRANSFER",
        "amount": 1250.0,
        "oldbalanceOrg": 2000.0,
        "newbalanceOrig": 750.0,
        "oldbalanceDest": 20.0,
        "newbalanceDest": 1270.0,
    }
    frame_features = build_feature_vector(row)
    transaction = Transaction(
        step=row["step"],
        transaction_type=row["type"],
        amount=row["amount"],
        old_balance_org=row["oldbalanceOrg"],
        new_balance_orig=row["newbalanceOrig"],
        old_balance_dest=row["oldbalanceDest"],
        new_balance_dest=row["newbalanceDest"],
    )
    assert frame_features == transaction_features(transaction)
    assert len(frame_features) == len(FEATURE_NAMES)


def test_model_analysis_returns_probability_and_feature_explanations():
    transaction = Transaction(
        step=1,
        transaction_type="TRANSFER",
        amount=181.0,
        old_balance_org=181.0,
        new_balance_orig=0.0,
        old_balance_dest=0.0,
        new_balance_dest=181.0,
    )
    result = assess_transaction(transaction)
    assert 0.0 <= result["fraud_probability"] <= 1.0
    assert result["overall_risk_score"] == round(result["fraud_probability"] * 100, 1)
    assert result["risk_level"] in {"low", "medium", "high"}
    assert result["model_classification"] == (
        "fraud"
        if result["fraud_probability"] >= result["classification_threshold"]
        else "legitimate"
    )
    assert result["model_version"] == "safepay-logistic-paysim-v1"
    assert result["anomaly_score"] == 0.0
    assert result["anomaly_status"] == "unavailable"
    assert result["anomaly_score"] != result["fraud_probability"]
    assert "Top model signals" in result["explanation"]
    assert "High-risk review threshold" in result["explanation"]


def test_training_excludes_account_ids_and_flagged_fraud_from_features():
    assert "nameOrig" not in REQUIRED_COLUMNS
    assert "nameDest" not in REQUIRED_COLUMNS
    assert "isFlaggedFraud" not in REQUIRED_COLUMNS
    assert "isFraud" in REQUIRED_COLUMNS
    assert "transaction type TRANSFER" in FEATURE_NAMES


def test_evaluation_metrics_handle_tied_probability_scores():
    metrics = evaluate(
        bytearray([1, 0, 1, 0]),
        array("d", [0.8, 0.8, 0.2, 0.1]),
        threshold=0.8,
    )
    assert metrics["average_precision"] == 0.5833333333333333
    assert metrics["roc_auc"] == 0.625
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
