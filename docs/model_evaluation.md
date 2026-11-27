# PaySim model evaluation

## Dataset and protocol

The model was trained from `PS_20174392719_1491204439457_log.csv` using `isFraud` as the target. The source contains 6,362,620 rows and 8,213 fraud labels (about 0.129%). `isFlaggedFraud` is not a model feature; it marks only 16 rows and is excluded to avoid target leakage. Account identifiers are also excluded.

The reproducible seeded split assigns 70% of rows to training, 10% to probability calibration, 10% to threshold selection, and 10% to final testing. To keep training compact, all fraud rows and a random 5% of legitimate training rows are sampled. Calibration, validation, and test retain the natural class prevalence. A logistic regression is fit using mini-batch gradient descent; case-control sampling is corrected before sigmoid probability calibration. The high-risk threshold is selected by validation F1 and evaluated once on the held-out test split.

## Held-out test results

| Metric | Result |
|---|---:|
| Test rows | 636,944 |
| Fraud rows | 767 |
| Average precision (PR-AUC) | 0.6086 |
| ROC-AUC | 0.9777 |
| Brier score | 0.000669 |
| Validation-selected threshold | 14.14% |
| Precision at threshold | 62.69% |
| Recall at threshold | 54.11% |
| F1 at threshold | 0.5808 |
| False-positive rate | 0.0388% |
| True positives / false positives | 415 / 247 |
| False negatives / true negatives | 352 / 635,930 |

The test-set fraud prevalence is about 0.120%. Average precision is reported alongside ROC-AUC because the labels are highly imbalanced. Exact split counts, calibration parameters, and all metric values are generated in `backend/ml/saved_models/evaluation.json` by the training command.

## Interpretation and limitations

These are reproducible held-out results on a synthetic dataset, not evidence of performance on real financial transactions. The random row split can share simulator patterns across splits and does not measure future-time or institution-to-institution generalization. The selected threshold optimizes F1 for this dataset and is not an operational policy. Validate on representative, independently sourced, time-separated data and choose thresholds with analysts and compliance stakeholders before any real use. Every score requires human review.