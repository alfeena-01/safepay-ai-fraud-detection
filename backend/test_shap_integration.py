import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from backend.app.services.risk_investigation_engine.shap_explainer import (
    generate_shap_explanation
)


# 1. Create sample transaction dataset

data = pd.DataFrame({
    "amount": [100, 500, 1000, 5000, 10000, 200, 800, 9000, 300, 7000],
    "transaction_hour": [10, 12, 14, 2, 3, 11, 15, 1, 13, 4],
    "failed_attempts": [0, 0, 1, 4, 5, 0, 1, 6, 0, 3],
    "location_mismatch": [0, 0, 0, 1, 1, 0, 0, 1, 0, 1]
})

labels = [0, 0, 0, 1, 1, 0, 0, 1, 0, 1]


# 2. Train sample ML model

X_train, X_test, y_train, y_test = train_test_split(
    data,
    labels,
    test_size=0.2,
    random_state=42,
    stratify=labels
)

model = RandomForestClassifier(
    n_estimators=50,
    random_state=42
)

model.fit(X_train, y_train)


# 3. Generate SHAP explanation

background_data = X_train

transaction_data = X_test.iloc[[0]]

result = generate_shap_explanation(
    model=model,
    background_data=background_data,
    transaction_data=transaction_data
)


# 4. Display results

print("\n===== SHAP INTEGRATION TEST =====")

print("Fraud Probability:", result["fraud_probability"])

print("\nFeature Explanations:")

for item in result["feature_explanations"]:
    print(item)

print("\nBase Value:", result["base_value"])

print("\nSHAP INTEGRATION SUCCESSFUL!")