Historical product-change review: 2021–2024

This directory records the historical extension of the agreed product-change magnitude rubric. Earlier release-type and enhancement labels remain unchanged. The older primary_scope and title_stage fields remain unassessed.

Inputs
- protocol.json: review population, sample seed, and original source hashes.
- batch0.json through batch2.json: all 9,247 saved official source announcements, assigned in URL-sorted interleaved batches. Each row has date, title, source URL, and saved source text.
- baseline_decisions.json and baseline_2025_2026.csv/json: frozen recent decisions/exports. The historical extension must not change these 4,920 ratings, reasons, or provenance.

Initial classification
- ratings0.tsv through ratings2.tsv: one individually reasoned source reading for every assigned row. Columns are index, level, source-specific reason, and confidence. There is no header. Initial reviewers did not see the audit sample or other readers' labels.
- initial_frozen.json: hashes preventing later edits to these predictions.

Fresh sample
- sample.json: 200 records selected before classification by seeded pseudorandom SHA256(seed + source URL) ranking without replacement from all 9,247 historical rows.
- sample_reader_a.tsv and sample_reader_b.tsv: independent source readings, blinded to production ratings and each other.
- reader_a_frozen.json: first reader frozen before seeing other labels.
- reference_protocol.json: all disagreements/low-confidence cases and 20 agreement checks selected for a third source-only reader.
- third_reading.json and sample_reader_c.tsv: independent source-only third reading. Local indices map to sample_index in the input.
- reference.tsv/json: final adjudicated reference used for scoring. The original frozen version and one later context correction are described below.
- reference_frozen.json: hashes and provenance for the reference.
- reference_v1: the original reference frozen before targeted review. During targeted review, an earlier official Wickr preview exposed one reference error (sample 197, 5 changed to U). Both versions and score sensitivity are retained; the correction preceded sample prediction scoring.
- reference_context.json and reference_adjudication.json: supplementary official context and adjudication rationale.
- metrics.json, row_audit.csv/json and report.html: initial prediction agreement with that reference, before any audit corrections.

Targeted review and publication
- cross_review_overrides.json: source-justified corrections from targeted review, separate from the blind sample.
- final_review.json: replayable final overrides, counts, hashes, and changed-record count. Frozen sample-reference decisions take precedence on sampled records.

The reference is AI-generated, not human ground truth. Confidence intervals describe random-sample uncertainty, not shared model bias. Accuracy on rare levels cannot be established from a handful of sampled examples. Do not present agreement after applying sample corrections as fresh accuracy.

Reproduce from the explorer root with its Python dependencies installed and the server stopped:
python product_change/historical_audit.py score
python product_change/build.py
python product_change/charts.py
python product_change/verify.py

Do not rerun prepare or freeze to reproduce published results: those commands are review-authoring steps. The score/build commands replay frozen decisions and verify saved source text; they do not rerun an AI model. Coverage means all records in this collected corpus are classified, not that every AWS publication is proven present.

Cross-review evidence
- cross_review_final.json records all 233 initially high-rated records checked by a second reader.
- cross_review_root.tsv, cross_review_d.tsv, and cross_review_e.tsv preserve the source readings.
- Files named high_scope_queue or high_scope_root_pending are working queue snapshots, not final coverage counts.
- final_review.json records 69 changed records after targeted review and sample-reference corrections.

See ../../RELEASE_NOTES.md for the release-wide interpretation and remaining limits.
