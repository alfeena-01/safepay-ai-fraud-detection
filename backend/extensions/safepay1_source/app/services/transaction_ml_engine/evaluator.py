from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)


def evaluate_model(model, X_test, y_test):

    predictions = model.predict(X_test)

    results = {
        "accuracy": accuracy_score(y_test, predictions),
        "precision": precision_score(
            y_test, predictions, zero_division=0
        ),
        "recall": recall_score(
            y_test, predictions, zero_division=0
        ),
        "f1_score": f1_score(
            y_test, predictions, zero_division=0
        )
    }

    print("Model Evaluation Results")
    print(results)
    print(classification_report(
        y_test, predictions, zero_division=0
    ))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, predictions))

    return results