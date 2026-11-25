# User manual

1. Start the backend and frontend using the repository README instructions.
2. Open the dashboard and check that the API is reachable; empty cards are expected before data is loaded.
3. Go to **Transaction Monitoring** and upload your UTF-8 PaySim CSV. Review the inserted/duplicate counts and dataset summary.
4. Search/filter the transaction table and open a row for its details.
5. Before risk analysis, train or install the model as described in the README. In **Risk Analysis**, select a transaction and run model analysis. The result includes a calibrated fraud probability and the strongest contributing signals. High-risk results create an alert for review.
6. In **Account Network**, enter a sender/receiver account ID from the CSV to see connected accounts and flagged edges.
7. Create an investigation case from the case page, update its status/priority, and add notes.
8. Generate a report from a case or transaction. Use the browser print dialog to save/export it.

The model is trained and evaluated on synthetic PaySim data; results are illustrative and not validated for production. Treat alerts as analyst decision support, not as financial decisions.