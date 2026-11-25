
import numpy as np
import pandas as pd
import shap


def generate_shap_explanation(
    model,
    background_data,
    transaction_data,
    top_n=5
):
    """
    Explain a fraud prediction using SHAP.

    model:
        Trained binary classification model.

    background_data:
        Representative training DataFrame.

    transaction_data:
        DataFrame containing exactly one transaction.

    Returns:
        Dictionary containing fraud probability
        and feature-level SHAP explanations.
    """

    if not isinstance(background_data, pd.DataFrame):
        raise ValueError("background_data must be a DataFrame")

    if not isinstance(transaction_data, pd.DataFrame):
        raise ValueError("transaction_data must be a DataFrame")

    if background_data.empty:
        raise ValueError("Background data cannot be empty")

    if len(transaction_data) != 1:
        raise ValueError("Provide exactly one transaction")

    if list(background_data.columns) != list(transaction_data.columns):
        raise ValueError("Feature columns must match in the same order")

    if not hasattr(model, "predict_proba"):
        raise ValueError("Model must support predict_proba")

    # Identify the fraud class (class 1)
    classes = list(model.classes_)

    if 1 not in classes:
        raise ValueError("Model must contain fraud class 1")

    fraud_index = classes.index(1)

    # Predict fraud probability
    probabilities = model.predict_proba(transaction_data)
    fraud_probability = float(probabilities[0][fraud_index])

    # Create SHAP explainer for model probabilities
    explainer = shap.Explainer(
        model.predict_proba,
        background_data
    )

    # Calculate SHAP values
    feature_count = transaction_data.shape[1]

    explanation = explainer(
        transaction_data,
        max_evals=max(100, 2 * feature_count + 1)
    )

    shap_values = np.asarray(explanation.values)
    base_values = np.asarray(explanation.base_values)

    # Select the fraud-class SHAP values
    if shap_values.ndim == 3:
        contributions = shap_values[0, :, fraud_index]
    elif shap_values.ndim == 2:
        contributions = shap_values[0]
    else:
        raise ValueError("Unexpected SHAP output shape")

    if base_values.ndim == 2:
        base_value = float(base_values[0, fraud_index])
    elif base_values.ndim == 1:
        base_value = float(base_values[0])
    else:
        base_value = float(base_values)

    # Build feature explanations
    feature_explanations = []

    for index, feature_name in enumerate(transaction_data.columns):

        contribution = float(contributions[index])
        feature_value = transaction_data.iloc[0, index]

        if isinstance(feature_value, np.generic):
            feature_value = feature_value.item()

        feature_explanations.append({
            "feature": str(feature_name),
            "feature_value": feature_value,
            "shap_value": round(contribution, 6),
            "impact": (
                "Increases fraud probability"
                if contribution > 0
                else "Decreases fraud probability"
                if contribution < 0
                else "No impact"
            )
        })

    # Show the most influential features first
    feature_explanations.sort(
        key=lambda item: abs(item["shap_value"]),
        reverse=True
    )

    return {
        "fraud_probability": round(fraud_probability, 6),
        "base_value": round(base_value, 6),
        "explained_class": 1,
        "feature_explanations": feature_explanations[:top_n]
    }
