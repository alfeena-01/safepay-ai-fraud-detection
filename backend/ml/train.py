import sys
import joblib
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.transaction_ml_engine.data_loader import load_dataset
from app.services.transaction_ml_engine.preprocessing import clean_dataset
from app.services.transaction_ml_engine.feature_engineering import create_features
from app.services.transaction_ml_engine.trainer import train_model
from app.services.transaction_ml_engine.evaluator import evaluate_model


DATA_PATH = BACKEND_DIR / "data" / "raw" / "paysim.csv"

MODEL_PATH = BACKEND_DIR / "ml" / "saved_models" / "fraud_model.pkl"


def main():

    print("Loading dataset...")

    data = load_dataset(DATA_PATH)

    print("\nCleaning dataset...")

    data = clean_dataset(data)

    print("\nCreating ML features...")

    features = create_features(data)

    target = data["isFraud"].astype(int)

    print("\nTraining Random Forest model...")

    model, X_train, X_test, y_train, y_test = train_model(
        features,
        target
    )

    print("\nEvaluating model...")

    results = evaluate_model(model, X_test, y_test)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        {
            "model": model,
            "feature_columns": list(features.columns)
        },
        MODEL_PATH
    )

    print("\nModel training completed!")

    print("\nModel Performance:")

    for metric, value in results.items():

        if metric not in ["confusion_matrix", "classification_report"]:
            print(f"{metric}: {value}")

    print("\nConfusion Matrix:")
    print(results["confusion_matrix"])

    print("\nModel saved successfully!")
    print(MODEL_PATH)


if __name__ == "__main__":
    main()