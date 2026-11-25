import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from backend.app.services.risk_investigation_engine.risk_investigation_service import (
    investigate_transaction
)


# 1. Sample Dataset

data = pd.DataFrame({
    "amount": [100, 500, 1000, 5000, 10000,
               200, 800, 9000, 300, 7000],

    "transaction_hour": [10, 12, 14, 2, 3,
                         11, 15, 1, 13, 4],

    "failed_attempts": [0, 0, 1, 4, 5,
                        0, 1, 6, 0, 3],

    "location_mismatch": [0, 0, 0, 1, 1,
                          0, 0, 1, 0, 1]
})

labels = [0, 0, 0, 1, 1, 0, 0, 1, 0, 1]


# 2. Train ML Model

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


# 3. Prepare Transaction

transaction = {
    "transaction_id": "TXN-1001",

    "features": X_test.iloc[0].to_dict(),

    "anomaly_score": 0.85,

    "behaviour_deviation": 0.75,

    "graph_risk": 0.80,

    "rule_evidence": [
        "Unusual transaction detected",
        "Suspicious account activity"
    ]
}


# 4. Run Investigation

result = investigate_transaction(
    transaction=transaction,
    model=model,
    background_data=X_train
)




print("\n===== FINAL INVESTIGATION RESULT =====")

for key, value in result.items():

    print(f"\n{key}: {value}")


print("\n======================================")
print("FINAL INVESTIGATION TEST SUCCESSFUL!")
print("======================================")    
