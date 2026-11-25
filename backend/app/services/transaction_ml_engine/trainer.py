from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier


def train_model(features, target):
    """
    Train a memory-friendly Random Forest fraud detection model.
    """

    # Split dataset into training and testing data
    X_train, X_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42,
        stratify=target
    )

    # Create memory-friendly Random Forest model
    model = RandomForestClassifier(
        n_estimators=50,
        max_depth=15,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=2
    )

    # Train the model
    model.fit(X_train, y_train)

    return model, X_train, X_test, y_train, y_test