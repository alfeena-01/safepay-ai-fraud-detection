import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Mapping

from app.database.models import Transaction


MODEL_PATH = Path(__file__).resolve().parents[3] / "ml" / "saved_models" / "safepay_fraud_model.json"
FEATURE_VERSION = "paysim-logistic-v1"
TRANSACTION_TYPES = ("CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER", "UNKNOWN")
NUMERIC_COLUMNS = (
    "step",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
)
FEATURE_NAMES = (
    "step",
    "amount",
    "origin balance before",
    "origin balance after",
    "destination balance before",
    "destination balance after",
    *(f"transaction type {transaction_type}" for transaction_type in TRANSACTION_TYPES),
)


class ModelUnavailableError(RuntimeError):
    pass


def _number(value: object) -> float:
    try:
        number = float(value) if value not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0
    return max(number, 0.0) if math.isfinite(number) else 0.0


def build_feature_vector(record: Mapping[str, object]) -> list[float]:
    features = [math.log1p(_number(record.get(column))) for column in NUMERIC_COLUMNS]
    transaction_type = str(record.get("type") or "UNKNOWN").upper()
    features.extend(float(transaction_type == known_type) for known_type in TRANSACTION_TYPES)
    if transaction_type not in TRANSACTION_TYPES:
        features[-1] = 1.0
    return features


def transaction_features(transaction: Transaction) -> list[float]:
    return build_feature_vector({
        "step": transaction.step,
        "type": transaction.transaction_type,
        "amount": transaction.amount,
        "oldbalanceOrg": transaction.old_balance_org,
        "newbalanceOrig": transaction.new_balance_orig,
        "oldbalanceDest": transaction.old_balance_dest,
        "newbalanceDest": transaction.new_balance_dest,
    })


@lru_cache(maxsize=1)
def load_model() -> dict:
    if not MODEL_PATH.is_file():
        raise ModelUnavailableError(
            "The trained SafePay model is not installed. Run "
            "`python -m ml.train_explainable --dataset <path-to-labeled-csv>` from the backend directory."
        )
    try:
        with MODEL_PATH.open(encoding="utf-8") as model_file:
            artifact = json.load(model_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelUnavailableError(f"Could not read the trained SafePay model: {exc}") from exc
    if artifact.get("feature_version") != FEATURE_VERSION:
        raise ModelUnavailableError(
            f"Unsupported model feature version: {artifact.get('feature_version')!r}."
        )
    if len(artifact.get("coefficients", [])) != len(FEATURE_NAMES):
        raise ModelUnavailableError("The trained model has an incompatible feature count.")
    return artifact


def _scaled_features(features: list[float], artifact: dict) -> list[float]:
    return [
        (value - mean) / scale
        for value, mean, scale in zip(
            features, artifact["means"], artifact["scales"], strict=True
        )
    ]


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-min(value, 709.0)))
    exp_value = math.exp(max(value, -709.0))
    return exp_value / (1.0 + exp_value)


def explain_prediction(features: list[float], artifact: dict) -> str:
    scaled = _scaled_features(features, artifact)
    coefficients = artifact["coefficients"]
    calibration_slope = artifact["calibration_slope"]
    contributions = [
        value * coefficient * calibration_slope
        for value, coefficient in zip(scaled, coefficients, strict=True)
    ]
    ranked = sorted(
        zip(FEATURE_NAMES, contributions, strict=True),
        key=lambda item: abs(item[1]),
        reverse=True,
    )[:4]

    lines = [
        "Top model signals (calibrated log-odds; positive raises risk, negative lowers it):"
    ]
    for name, contribution in ranked:
        direction = "increased" if contribution >= 0 else "reduced"
        lines.append(f"- {name} {direction} the score ({contribution:+.2f}).")
    threshold = artifact["decision_threshold"]
    lines.append(f"High-risk review threshold: {threshold:.2%} fraud probability.")
    lines.append("Account-network relationships are not features in this model.")
    return "\n".join(lines)


def assess_transaction(transaction: Transaction) -> dict[str, float | str]:
    artifact = load_model()
    features = transaction_features(transaction)
    scaled = _scaled_features(features, artifact)
    raw_logit = artifact["intercept"] + sum(
        coefficient * value
        for coefficient, value in zip(
            artifact["coefficients"], scaled, strict=True
        )
    )
    calibrated_logit = (
        artifact["calibration_intercept"]
        + artifact["calibration_slope"] * raw_logit
    )
    probability = _sigmoid(calibrated_logit)
    threshold = float(artifact["decision_threshold"])
    level = "high" if probability >= threshold else "medium" if probability >= threshold * 0.25 else "low"
    action = (
        "Escalate for analyst review"
        if level == "high"
        else "Review supporting context"
        if level == "medium"
        else "Continue routine monitoring"
    )
    return {
        "fraud_probability": round(probability, 6),
        "anomaly_score": round(probability, 6),
        "graph_risk": 0.0,
        "overall_risk_score": round(probability * 100, 1),
        "risk_level": level,
        "explanation": explain_prediction(features, artifact),
        "recommended_action": action,
        "model_version": artifact["model_version"],
    }
