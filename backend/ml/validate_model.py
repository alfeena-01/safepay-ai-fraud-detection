import sys
import joblib
import pandas as pd
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.transaction_ml_engine.preprocessing import clean_dataset
from app.services.transaction_ml_engine.feature_engineering import create_features
from app.services.transaction_ml_engine.evaluator import evaluate_model

DATA_PATH = BACKEND_DIR / "data" / "raw" / "paysim.csv"
MODEL_PATH = BACKEND_DIR / "ml" / "saved_models" / "fraud_model.pkl"

def load_independent_sample():

    print("Loading independent test data...")

    test_chunks = []

    columns = [
        "step", "type", "amount",
        "oldbalanceOrg", "newbalanceOrig",
        "oldbalanceDest", "newbalanceDest",
        "isFraud"
    ]

    for i, chunk in enumerate(
        pd.read_csv(DATA_PATH, usecols=columns, chunksize=500000)
    ):

        training_indices = chunk.sample(
            frac=0.08,
            random_state=42 + i
        ).index

        remaining = chunk.drop(index=training_indices)

        test_sample = remaining.sample(
            frac=0.08,
            random_state=1000 + i
        )

        test_chunks.append(test_sample)

        print(f"Processed chunk: {i + 1}")

    if not test_chunks:
        raise ValueError("No test data found!")

    return pd.concat(test_chunks, ignore_index=True)


def main():

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    data = clean_dataset(load_independent_sample())

    features = create_features(data)
    target = data["isFraud"].astype(int)

    saved_data = joblib.load(MODEL_PATH)

    model = saved_data["model"]
    features = features[saved_data["feature_columns"]]

    print("\nIndependent Test Dataset")
    print("Transactions:", len(data))
    print("Fraud:", int(target.sum()))
    print("Legitimate:", int((target == 0).sum()))

    print("\nValidating model...")

    results = evaluate_model(model, features, target)

    for metric, value in results.items():
        print(f"\n{metric}:")
        print(value)


if __name__ == "__main__":
    main()