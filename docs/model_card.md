# SafePay PaySim logistic model

## Summary

- **Model version:** `safepay-logistic-paysim-v1`
- **Model type:** Logistic regression with sigmoid probability calibration
- **Training data:** Synthetic PaySim transaction CSV, `isFraud` target
- **Output:** Calibrated fraud probability, risk band, and additive feature-contribution explanation
- **Primary use:** Educational analyst-review workflow and software demonstration

## Inputs and explanation

The model uses transaction step, amount, origin/destination balances, and one-hot encoded transaction type. Numeric inputs are non-negative `log1p` transformed and standardized. Account identifiers and `isFlaggedFraud` are excluded. Explanation values are each feature's contribution to calibrated log-odds relative to the standardized baseline; positive values increase and negative values decrease the model score. These are associations learned by the model, not causal findings. Account-network relationships are not modeled.

## Evaluation

The dataset was split by seeded random row assignment into 70% training, 10% calibration, 10% validation, and 10% test. Legitimate training rows were randomly downsampled to 5%; all fraud rows were retained. Probability calibration used the calibration split, the high-risk threshold was selected by validation F1, and results were reported on the untouched test split. See [model evaluation](./model_evaluation.md) for the held-out metrics and split details.

## Limitations and use restrictions

PaySim is synthetic and cannot represent all real fraud mechanisms, customer populations, institutions, or operational constraints. Random row splits do not test temporal drift or generalization to real accounts. The F1-selected threshold is dataset-specific. False positives and false negatives remain; use scores only as decision support for human analysts. Do not use for automatic declines, account restrictions, legal conclusions, or customer-impacting decisions. This project has no production validation, privacy review, or deployment controls.