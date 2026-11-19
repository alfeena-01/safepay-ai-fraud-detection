# Dataset documentation

## PaySim CSV support

The upload API accepts UTF-8 CSV files up to 1 GB. Header names are case-insensitive. Required headers are `type`, `amount`, `nameOrig`, and `nameDest`. The standard PaySim fields are recognized:

`step`, `type`, `amount`, `nameOrig`, `oldbalanceOrg`, `newbalanceOrig`, `nameDest`, `oldbalanceDest`, `newbalanceDest`, `isFraud`, `isFlaggedFraud`

`transactionId` is optional. When it is absent, SafePay creates a deterministic ID from the file content and row number, allowing the same file to be uploaded again without importing those rows twice. The file is validated in a streaming pass and imported in 500-row batches within one database transaction; it is not loaded all at once into memory or written to a tracked file.

## Missing values and validation

- Empty amount and balance fields are treated as zero.
- Empty step is stored as null.
- Empty account IDs are stored as null.
- Empty transaction type is stored as `UNKNOWN`.
- Fraud indicators accept `1`, `true`, or `yes` (case-insensitive); other values are false.
- Invalid/negative numeric values reject the complete upload before database insertion.
- Existing or repeated transaction IDs are skipped and counted.
- Required headers must be present even if individual row values are blank.

Uploaded fraud labels are ground-truth dataset fields, not model predictions. The API risk-analysis placeholder is documented separately and is not trained using those labels.