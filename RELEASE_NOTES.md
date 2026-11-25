# AWS announcement explorer: 25 November 2026

This release extends product-change magnitude classification to every collected announcement from 2021–2024. The release contains 14,167 announcements through 28 October 2026.

Classification describes the size of the announced product change itself. The categories do not measure customer consequences, engineering effort, or business value. AI readers produced the classifications and audit references.

## Changes in this release

- Added individual source readings for 9,247 historical announcements.
- Preserved all 4,920 existing recent ratings, reasons, and provenance entries.
- Applied 69 historical corrections after sample and targeted review.
- Added monthly charts and annual comparisons across six years.
- Updated CSV, JSON, DuckDB, and service comparison exports.
- Added a fresh historical audit with saved sources, decisions, and reasons.

The annual comparison uses 1 January–28 October in every year. The monthly chart includes full earlier years and ends on 28 October 2026.

## Collected records by year

Every collected record has a magnitude decision, including explicit needs-review and outside-scale decisions.

| Year | Announcements |
| --- | ---: |
| 2021 | 2,084 |
| 2022 | 2,103 |
| 2023 | 2,715 |
| 2024 | 2,345 |
| 2025 | 2,663 |
| 2026, through 28 October | 2,257 |
| Total | 14,167 |

## Historical audit results

The fresh sample contains 200 records selected before classification. Initial readers did not see the sample selection. Two independent readers assessed every sampled announcement without seeing the production labels or each other's decisions. A third reader assessed disagreements, low-confidence cases, and selected agreements.

Initial classifications agreed with the final reference on 177 records, or 88.5%. The Wilson 95% interval is 83.3%–92.2%. This interval describes sample uncertainty; it does not account for shared AI bias.

The original frozen reference gave 88.0% agreement. During targeted review, earlier official context changed one reference decision about Wickr general availability. That correction preceded sample scoring. Both references remain available, so the effect of the revision is visible.

Among reference records assigned levels 1–5, agreement was 123 of 145, or 84.8%. The [historical audit report](product_change/historical_review/report.html) provides category results and uncertainty details. The [audit metrics](product_change/historical_review/metrics.json) contain the exact calculations.

All 233 initial historical level-4 and level-5 decisions received a second source reading. This targeted review checks existing high ratings; it cannot find every high-scope change assigned a lower rating.

The random sample contained two reference level-4 records, and the initial classifications missed both. The sample contained no reference level-5 records. Major-expansion and new-product trends therefore remain provisional. Agreement after applying sample corrections is not a new accuracy measurement.

## Validation completed

The release checks confirm unique source URLs, complete magnitude decisions, and exact historical source matches. The checks also confirm unchanged recent decisions and consistent exports, chart totals, service counts, and chart drill-down results.

A rebuild from an extracted archive reproduced 12 data, chart, and audit outputs byte for byte. The [reproduction evidence](release/reproduction.json) records their hashes. The [verification report](product_change/verification_report.txt) records the integrated check result.

Browser checks confirmed historical annual and monthly drill-down counts, the share view, and readable SVG charts. The release was tested with Python 3.13.7 and DuckDB 1.5.6 on macOS. Other operating systems have not been tested.

## Limits that remain

- Classification covers the collected corpus. Spot checks have not established exhaustive historical source coverage.
- All labels remain AI judgments. The audit does not establish human-validated accuracy.
- Historical magnitude decisions include 204 needs-review records. The complete corpus contains 226 needs-review records.
- The older `primary_scope` and `title_stage` fields remain unassessed for 2021–2024.
- Service tags are unknown on 246 historical rows. Service tags can overlap, so service totals must not be added together.
- Announcement counts are not counts of unique features or products. Preview, general availability, and regional rollout can produce separate announcements.
- The release contains no publications after 28 October 2026. The release date is not the collection cutoff.

Prioritise broader independent review of rare categories and historical collection coverage before making strong claims about category trends. Review this documentation whenever the corpus, rubric, or audit reference changes.
