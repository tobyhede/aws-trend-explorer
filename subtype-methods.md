# AWS enhancement subtype validation

Open audit.html for the decisions, rate comparisons, service-tag coverage and a linked AWS source for each reviewed record. announcements.csv, announcements.json and announcements.duckdb contain the full historical snapshot. Changes in this pass are confined to enhancement facets. The primary release types and URL-based counting convention come from the prior historical audit. Rates use January 1 through October 28 inclusive in every year, dividing by elapsed calendar weeks.

## Source readings and validation

Two agents read the same source text independently, without seeing existing labels. Source excerpts accompany positive readings. Sampling used year and five mutually exclusive groups based on the previous labels. Overlaps were assigned to service limit, then performance, then integration. Other labeled enhancements and unlabeled enhancements formed the last two groups. There were 29 populated year/group combinations. Two per combination formed the calibration sample and six others formed the fresh holdout. This deliberately samples rare labels and previously unlabeled rows. The holdout readers did not work on backlog classification. All holdout predictions were frozen before the lead compared them with the source readings.

holdout_metrics.csv supplies the raw confusion counts and a weighted comparison. The weighted totals scale each sampled group to its enhancement population after removing the two calibration records. The audit tests presence and absence of each target label; it does not test whether the primary enhancement cohort itself is complete. Precision is the proportion of assigned labels supported in the source readings. Recall is the proportion of source-supported labels found. Agent readings provide an independent comparison with remaining judgment at the boundaries. Other facets assigned during the backlog review did not receive this holdout test.

Final counts include the corrections on reviewed rows, subject to the protections for previous reviewed fields. The per-year rates and service comparisons report real labeled records. error_sensitivity.csv and change_sensitivity.csv are separate sampling diagnostics. They estimate the remaining effect of missed and extra labels, using the historical source groups and the holdout error pattern. The indicative resampling ranges use 3,000 seeded draws within strata and a finite-population correction. Six readings per stratum cannot identify all possible errors; a stratum with no observed errors contributes no sampled variability. The ranges omit primary-category errors and reviewer uncertainty.

Service comparisons use distinct AWS tags on each record. One announcement may count toward several services. Tag completeness is reported separately. Performance labels refer to AWS-reported changes in workloads, latency, throughput or quality. Prior coverage limits, including the absence of an independent complete historical inventory for 2021–2024, still apply.

## Reproduce

The bundle includes the historical source CSV, ontology, source readings and classification decisions. From the extracted archive root run these commands with Python, DuckDB, NumPy and matplotlib installed.

    python subtype_validation/sample_rows.py
    python subtype_validation/backlog.py
    python subtype_validation/build.py
    python subtype_validation/accuracy.py
    python subtype_validation/render.py

Decision inputs are URL-keyed. The saved reader files are the independent readings; regeneration of numeric outputs reuses them. De-identified sampling was not used; readers could see the source titles, URLs and bodies. Their input files omitted prior classifications.
