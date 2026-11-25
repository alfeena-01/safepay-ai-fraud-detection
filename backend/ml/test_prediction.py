import sys
import joblib
import pandas as pd
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.transaction_ml_engine.feature_engineering import create_features
from app.services.transaction_ml_engine.predictor import predict_transaction

MODEL_PATH = BACKEND_DIR / "ml" / "saved_models" / "fraud_model.pkl"

# Load trained model
saved_data = joblib.load(MODEL_PATH)

model = saved_data["model"]
feature_columns = saved_data["feature_columns"]

# Sample transaction
transaction = pd.DataFrame([{
    "step": 100,
    "type": "TRANSFER",
    "amount": 1000,
"oldbalanceOrg": 10000,
"newbalanceOrig": 9000,
"oldbalanceDest": 5000,
"newbalanceDest": 6000
}])

# Create features
features = create_features(transaction)

features = features[feature_columns]

# Predict transaction
result = predict_transaction(model, features)

print("\nSafePay Transaction Prediction")
print("--------------------------------")
print("Prediction:", result["status"])
print("Fraud Probability:", result["fraud_probability"], "%")