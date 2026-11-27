from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier


def train_fraud_model(X, y):

    categorical_columns = X.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    numerical_columns = X.select_dtypes(
        include=["number"]
    ).columns.tolist()

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"),
             categorical_columns),
            ("numerical", "passthrough", numerical_columns)
        ]
    )

    model = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(
            n_estimators=100,
            class_weight="balanced",
            random_state=42
        ))
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    model.fit(X_train, y_train)

    return model, X_test, y_test


def predict_fraud(model, transaction):

    prediction = model.predict(transaction)

    return prediction