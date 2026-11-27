import argparse
import csv
import json
import math
import random
from array import array
from pathlib import Path

from app.services.anomaly_detection_engine.model import (
    FEATURE_NAMES,
    FEATURE_VERSION,
    build_feature_vector,
)


MODEL_VERSION = "safepay-logistic-paysim-v1"
TRAIN_NEGATIVE_SAMPLE_RATE = 0.05
RANDOM_SEED = 42
EPOCHS = 25
BATCH_SIZE = 2048
LEARNING_RATE = 0.1
L2_PENALTY = 0.0001
REQUIRED_COLUMNS = {
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
}


def _read_rows(dataset_path: Path):
    with dataset_path.open("r", encoding="utf-8-sig", newline="") as dataset_file:
        reader = csv.DictReader(dataset_file)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing))}")
        yield from reader


def _label(row: dict[str, str], row_number: int) -> int:
    value = row.get("isFraud", "")
    if value not in {"0", "1"}:
        raise ValueError(f"Invalid isFraud value on CSV row {row_number}: {value!r}")
    return int(value)


def collect_training_sample(dataset_path: Path) -> tuple[array, bytearray, dict[str, int]]:
    split_rng = random.Random(RANDOM_SEED)
    sample_rng = random.Random(RANDOM_SEED + 1)
    feature_values = array("d")
    labels = bytearray()
    counts = {
        "rows": 0,
        "train_rows": 0,
        "train_rows_sampled": 0,
        "train_fraud_rows": 0,
        "calibration_rows": 0,
        "calibration_fraud_rows": 0,
        "validation_rows": 0,
        "validation_fraud_rows": 0,
        "test_rows": 0,
        "test_fraud_rows": 0,
    }

    for row_number, row in enumerate(_read_rows(dataset_path), start=2):
        label = _label(row, row_number)
        split = split_rng.random()
        counts["rows"] += 1
        if split < 0.7:
            counts["train_rows"] += 1
            counts["train_fraud_rows"] += label
            if label or sample_rng.random() < TRAIN_NEGATIVE_SAMPLE_RATE:
                feature_values.extend(build_feature_vector(row))
                labels.append(label)
                counts["train_rows_sampled"] += 1
        elif split < 0.8:
            counts["calibration_rows"] += 1
            counts["calibration_fraud_rows"] += label
        elif split < 0.9:
            counts["validation_rows"] += 1
            counts["validation_fraud_rows"] += label
        else:
            counts["test_rows"] += 1
            counts["test_fraud_rows"] += label

    if not counts["rows"]:
        raise ValueError(f"No transaction rows were found in {dataset_path}.")
    if counts["train_fraud_rows"] == 0 or counts["train_fraud_rows"] == counts["train_rows"]:
        raise ValueError("The training split must contain both fraud and legitimate transactions.")
    if not labels or not any(labels) or all(labels):
        raise ValueError("The sampled training data must contain both classes.")
    return feature_values, labels, counts


def standardize_training_data(
    feature_values: array, row_count: int
) -> tuple[list[float], list[float]]:
    feature_count = len(FEATURE_NAMES)
    sums = [0.0] * feature_count
    squared_sums = [0.0] * feature_count
    for row_index in range(row_count):
        start = row_index * feature_count
        for column in range(feature_count):
            value = feature_values[start + column]
            sums[column] += value
            squared_sums[column] += value * value

    means = [value / row_count for value in sums]
    scales = [
        math.sqrt(max(squared_sums[index] / row_count - means[index] ** 2, 1e-12))
        for index in range(feature_count)
    ]
    for row_index in range(row_count):
        start = row_index * feature_count
        for column in range(feature_count):
            feature_values[start + column] = (
                feature_values[start + column] - means[column]
            ) / scales[column]
    return means, scales


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-min(value, 709.0)))
    exp_value = math.exp(max(value, -709.0))
    return exp_value / (1.0 + exp_value)


def train_logistic_regression(
    feature_values: array, labels: bytearray, row_count: int
) -> tuple[float, list[float]]:
    feature_count = len(FEATURE_NAMES)
    coefficients = [0.0] * feature_count
    intercept = 0.0
    order = list(range(row_count))
    rng = random.Random(RANDOM_SEED + 2)

    for _ in range(EPOCHS):
        rng.shuffle(order)
        for batch_start in range(0, row_count, BATCH_SIZE):
            batch = order[batch_start:batch_start + BATCH_SIZE]
            gradient = [0.0] * feature_count
            intercept_gradient = 0.0
            for row_index in batch:
                start = row_index * feature_count
                logit = intercept
                for column in range(feature_count):
                    logit += coefficients[column] * feature_values[start + column]
                error = _sigmoid(logit) - labels[row_index]
                intercept_gradient += error
                for column in range(feature_count):
                    gradient[column] += error * feature_values[start + column]

            batch_size = len(batch)
            intercept -= LEARNING_RATE * intercept_gradient / batch_size
            for column in range(feature_count):
                coefficients[column] -= LEARNING_RATE * (
                    gradient[column] / batch_size + L2_PENALTY * coefficients[column]
                )

    return intercept, coefficients


def _raw_logit(
    row: dict[str, str],
    means: list[float],
    scales: list[float],
    intercept: float,
    coefficients: list[float],
) -> float:
    features = build_feature_vector(row)
    return intercept + sum(
        coefficient * ((value - mean) / scale)
        for value, mean, scale, coefficient in zip(
            features, means, scales, coefficients, strict=True
        )
    )


def collect_holdout_scores(
    dataset_path: Path,
    means: list[float],
    scales: list[float],
    intercept: float,
    coefficients: list[float],
) -> dict[str, tuple[array, bytearray]]:
    split_rng = random.Random(RANDOM_SEED)
    holdouts = {
        name: (array("d"), bytearray())
        for name in ("calibration", "validation", "test")
    }
    for row_number, row in enumerate(_read_rows(dataset_path), start=2):
        label = _label(row, row_number)
        split = split_rng.random()
        if split < 0.7:
            continue
        split_name = "calibration" if split < 0.8 else "validation" if split < 0.9 else "test"
        scores, labels = holdouts[split_name]
        scores.append(_raw_logit(row, means, scales, intercept, coefficients))
        labels.append(label)
    for split_name, (_, labels) in holdouts.items():
        if not labels or not any(labels) or all(labels):
            raise ValueError(f"The {split_name} split must contain both classes.")
    return holdouts


def fit_calibrator(scores: array, labels: bytearray) -> tuple[float, float]:
    intercept = 0.0
    slope = 1.0
    for _ in range(30):
        gradient_intercept = 0.0
        gradient_slope = 0.0
        hessian_intercept = 0.0
        hessian_cross = 0.0
        hessian_slope = 1e-8
        for score, label in zip(scores, labels, strict=True):
            probability = _sigmoid(intercept + slope * score)
            error = probability - label
            weight = probability * (1.0 - probability)
            gradient_intercept += error
            gradient_slope += error * score
            hessian_intercept += weight
            hessian_cross += weight * score
            hessian_slope += weight * score * score
        determinant = hessian_intercept * hessian_slope - hessian_cross**2
        if determinant <= 1e-12:
            break
        intercept_step = (
            gradient_intercept * hessian_slope - gradient_slope * hessian_cross
        ) / determinant
        slope_step = (
            gradient_slope * hessian_intercept - gradient_intercept * hessian_cross
        ) / determinant
        intercept -= intercept_step
        slope -= slope_step
        if max(abs(intercept_step), abs(slope_step)) < 1e-7:
            break
    if not math.isfinite(slope) or slope <= 0:
        raise ValueError(
            "The calibration slope is not positive; the model did not learn a reliable "
            "fraud ranking, so no model artifact was saved."
        )
    return intercept, slope


def _calibrated_probabilities(
    scores: array, intercept: float, slope: float
) -> array:
    return array("d", (_sigmoid(intercept + slope * score) for score in scores))


def select_f1_threshold(labels: bytearray, probabilities: array) -> float:
    ranked = sorted(zip(probabilities, labels, strict=True), reverse=True)
    positives = sum(labels)
    true_positives = 0
    false_positives = 0
    best_f1 = -1.0
    best_threshold = ranked[0][0]
    index = 0
    while index < len(ranked):
        threshold = ranked[index][0]
        while index < len(ranked) and ranked[index][0] == threshold:
            if ranked[index][1]:
                true_positives += 1
            else:
                false_positives += 1
            index += 1
        precision = true_positives / (true_positives + false_positives)
        recall = true_positives / positives
        f1 = 2 * precision * recall / max(precision + recall, 1e-12)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
    return best_threshold


def evaluate(labels: bytearray, probabilities: array, threshold: float) -> dict:
    positives = sum(labels)
    negatives = len(labels) - positives
    true_positive = false_positive = false_negative = true_negative = 0
    brier_total = 0.0
    ranked_descending = sorted(zip(probabilities, labels, strict=True), reverse=True)
    average_precision_total = 0.0
    running_true_positive = 0
    index = 0
    while index < len(ranked_descending):
        score = ranked_descending[index][0]
        end = index
        group_positives = 0
        while end < len(ranked_descending) and ranked_descending[end][0] == score:
            group_positives += ranked_descending[end][1]
            end += 1
        running_true_positive += group_positives
        average_precision_total += (
            running_true_positive / end
        ) * group_positives
        index = end

    for probability, label in ranked_descending:
        brier_total += (probability - label) ** 2
        if probability >= threshold:
            if label:
                true_positive += 1
            else:
                false_positive += 1
        elif label:
            false_negative += 1
        else:
            true_negative += 1

    ranked_ascending = sorted(zip(probabilities, labels, strict=True))
    positive_rank_sum = 0.0
    index = 0
    while index < len(ranked_ascending):
        end = index + 1
        while end < len(ranked_ascending) and ranked_ascending[end][0] == ranked_ascending[index][0]:
            end += 1
        average_rank = ((index + 1) + end) / 2
        positive_rank_sum += average_rank * sum(
            label for _, label in ranked_ascending[index:end]
        )
        index = end

    precision = true_positive / max(true_positive + false_positive, 1)
    recall = true_positive / max(positives, 1)
    return {
        "average_precision": average_precision_total / max(positives, 1),
        "roc_auc": (
            (positive_rank_sum - positives * (positives + 1) / 2)
            / max(positives * negatives, 1)
        ),
        "brier_score": brier_total / len(labels),
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / max(precision + recall, 1e-12),
        "false_positive_rate": false_positive / max(negatives, 1),
        "true_positives": true_positive,
        "false_positives": false_positive,
        "false_negatives": false_negative,
        "true_negatives": true_negative,
    }


def train(dataset_path: Path, output_path: Path) -> dict:
    feature_values, labels, split_counts = collect_training_sample(dataset_path)
    train_rows = len(labels)
    means, scales = standardize_training_data(feature_values, train_rows)
    intercept, coefficients = train_logistic_regression(feature_values, labels, train_rows)
    del feature_values
    del labels

    training_prevalence = split_counts["train_fraud_rows"] / split_counts["train_rows"]
    sampled_prevalence = split_counts["train_fraud_rows"] / split_counts["train_rows_sampled"]
    intercept += math.log(
        (training_prevalence / (1.0 - training_prevalence))
        / (sampled_prevalence / (1.0 - sampled_prevalence))
    )

    holdouts = collect_holdout_scores(dataset_path, means, scales, intercept, coefficients)
    calibration_intercept, calibration_slope = fit_calibrator(*holdouts["calibration"])
    validation_probabilities = _calibrated_probabilities(
        holdouts["validation"][0], calibration_intercept, calibration_slope
    )
    threshold = select_f1_threshold(holdouts["validation"][1], validation_probabilities)
    test_probabilities = _calibrated_probabilities(
        holdouts["test"][0], calibration_intercept, calibration_slope
    )
    metrics = {
        "model_version": MODEL_VERSION,
        "dataset": dataset_path.name,
        "dataset_rows": split_counts["rows"],
        "label_column": "isFraud",
        "train_negative_sample_rate": TRAIN_NEGATIVE_SAMPLE_RATE,
        "seed": RANDOM_SEED,
        "splits": split_counts,
        "calibration": {
            "rows": len(holdouts["calibration"][1]),
            "fraud_rows": sum(holdouts["calibration"][1]),
            "intercept": calibration_intercept,
            "slope": calibration_slope,
        },
        "validation": evaluate(
            holdouts["validation"][1], validation_probabilities, threshold
        ),
        "test": evaluate(holdouts["test"][1], test_probabilities, threshold),
        "notes": (
            "Random row-level split; class prevalence preserved in calibration, validation, and test. "
            "Threshold selected by validation F1. Synthetic PaySim results are not production evidence."
        ),
    }
    artifact = {
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "feature_names": FEATURE_NAMES,
        "means": means,
        "scales": scales,
        "intercept": intercept,
        "coefficients": coefficients,
        "calibration_intercept": calibration_intercept,
        "calibration_slope": calibration_slope,
        "decision_threshold": threshold,
        "metrics": metrics,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(output_path)
    output_path.with_name("evaluation.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train and evaluate the explainable SafePay PaySim fraud model."
    )
    parser.add_argument("--dataset", type=Path, required=True, help="Labeled PaySim CSV path.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "saved_models" / "safepay_fraud_model.json",
        help="Trained model output path.",
    )
    arguments = parser.parse_args()
    if not arguments.dataset.is_file():
        parser.error(f"Dataset file does not exist: {arguments.dataset}")
    print(json.dumps(train(arguments.dataset, arguments.output), indent=2))


if __name__ == "__main__":
    main()
