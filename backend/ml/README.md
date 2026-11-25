# SafePay – AI Fraud Detection ML Engine

## Overview

The SafePay ML Engine detects potentially fraudulent financial transactions using a Random Forest classification algorithm.

It processes transaction data, performs feature engineering, trains a machine learning model, and predicts whether a transaction is fraudulent or legitimate.

## Dataset

- Dataset: PaySim
- Total Transactions: 6,362,620
- Fraud Transactions: 8,213
- Legitimate Transactions: 6,354,407
- Training Sample: Approximately 8% of the dataset

## Technologies Used

- Python
- Pandas
- Scikit-learn
- Joblib

## ML Modules

- `data_loader.py` – Loads and samples transaction data.
- `preprocessing.py` – Cleans and prepares the dataset.
- `feature_engineering.py` – Creates useful features for fraud detection.
- `trainer.py` – Trains the Random Forest classification model.
- `predictor.py` – Predicts transaction status and fraud probability.
- `evaluator.py` – Evaluates model performance.

## Model Training

Run from the backend directory:

```bash
python ml/train.py
```

## Model Evaluation

```bash
python ml/evaluate.py
```

## Independent Model Validation

```bash
python ml/validate_model.py
```

## Prediction Testing

```bash
python ml/test_prediction.py
```

## Model Performance

### Training Test Results

| Metric | Result |
|---|---:|
| Accuracy | 100.00% |
| Precision | 100.00% |
| Recall | 98.46% |
| F1 Score | 99.22% |

### Independent Validation Results

The model was tested using 468,287 transactions that were not included in the training sample.

| Metric | Result |
|---|---:|
| Accuracy | 100.00% |
| Precision | 100.00% |
| Recall | 98.72% |
| F1 Score | 99.36% |

### Validation Summary

- Total Test Transactions: 468,287
- Fraud Transactions: 626
- Legitimate Transactions: 467,661
- Correctly Detected Fraud Transactions: 618
- Missed Fraud Transactions: 8
- False Positives: 0

Note: Accuracy is displayed rounded to two decimal places. These validation results are from a separate sample of the same PaySim dataset, not a completely new real-world dataset. Further testing is required before production deployment.

## Saved Model

The trained model is saved at:

`ml/saved_models/fraud_model.pkl`

## Developer Responsibility

Member 1 – Transaction Data Processing and Machine Learning Engine.