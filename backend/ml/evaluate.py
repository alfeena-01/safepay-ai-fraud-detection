import sys
import joblib
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.transaction_ml_engine.preprocessing import clean_dataset
from app.services.transaction_ml_engine.feature_engineering import create_features
from app.services.transaction_ml_engine.evaluator import evaluate_model

DATA_PATH = BACKEND_DIR / "data" / "raw" / "paysim.csv"
MODEL_PATH = BACKEND_DIR / "ml" / "saved_models" / "fraud_model.pkl"


def load_training_sample():

    sample_chunks = []

    for chunk_number, chunk in enumerate(pd.read_csv(
        DATA_PATH,
        usecols=[
            "step",
            "type",
            "amount",
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest",
            "isFraud"
        ],
        chunksize=500000
    )):

        sample = chunk.sample(
            frac=0.08,
            random_state=42 + chunk_number
        )

        sample_chunks.append(sample)

    return pd.concat(sample_chunks, ignore_index=True)


def main():

    print("Loading dataset sample...")

    data = clean_dataset(load_training_sample())

    features = create_features(data)
    target = data["isFraud"].astype(int)

    saved_data = joblib.load(MODEL_PATH)

    model = saved_data["model"]
    features = features[saved_data["feature_columns"]]

    _, X_test, _, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42,
        stratify=target
    )

    print("\nEvaluating model...")

    results = evaluate_model(model, X_test, y_test)

    print("\nEvaluation Results")

    for metric, value in results.items():
        print(f"\n{metric}:")
        print(value)


if __name__ == "__main__":
    main()