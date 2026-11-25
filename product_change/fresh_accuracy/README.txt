Fresh classification accuracy audit — 24 November 2026

Scope: product-change magnitude for 2025 through 28 October 2026.
The fresh sample excludes every record included in the previous random audit, recorded adjudications, or agreed examples: 342 excluded, 4,578 eligible, 200 sampled. Sampling seed and frozen file hashes are in protocol.json.

Two independent AI readers label blind/sample.json without seeing frozen_predictions.json. A third independently reads disagreements, low-confidence cases and 20 randomly selected agreements. Reference adjudication occurs before predictions are scored. Original reader judgments are retained. This is an AI reference, not a human-validated gold standard.

Reproduce the selection checks and score from this directory with Python 3 (standard library only):
python3 score.py

To regenerate the third-reader selection from the frozen first two readings:
python3 score.py --prepare

Files: metrics.json contains Wilson intervals, confusion counts and category precision/recall; report.html is readable without running a server; row_audit.csv/json contain every sampled decision; mismatches.csv lists findings. Production classifications are not changed by this audit.
