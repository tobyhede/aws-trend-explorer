AWS announcement explorer
Release: 25 November 2026

Explore 14,167 collected AWS announcements from 1 January 2021 through
28 October 2026. Every record has a product-change magnitude decision.
Classifications and audit references are AI judgments. Historical collection
coverage has not been proven exhaustive.

Start the explorer

Extract aws_trend_explorer.zip into its own folder. Open a terminal in that
folder. The following commands are for macOS or Linux:

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python serve.py

Open http://127.0.0.1:8765 in your browser. Keep the terminal running.
Press Control-C in that terminal to stop the server. If the port is already
in use, run .venv/bin/python serve.py --port 8766 and open port 8766 instead.

The server listens on your computer only. The URL is not a shared website.

The release was tested on macOS with Python 3.13.7 and DuckDB 1.5.6.
Installing the dependency needs internet access. Browsing the bundled data
and rebuilding exports do not require an AWS account or model API access.
Other operating systems have not been tested.

Find the data and documentation

RELEASE_NOTES.md explains changes, audit results, validation, and remaining gaps.
DATA_GUIDE.md defines the exported fields, magnitude levels, and chart totals.
REPRODUCING.md explains rebuilding, checking, and sharing the release.

announcements.duckdb contains the announcements table.

product_change/announcements.csv and announcements.json contain all records,
including source URLs, saved announcement text, magnitude, reason, and basis.

product_change/method.html explains the rubric and reviewed examples.

product_change/historical_review/report.html contains the historical audit.

product_change/review.html contains the earlier 120-record recent audit.

product_change/fresh_accuracy contains the separate recent fresh-sample audit.

Classification coverage

The historical extension adds individual source readings for 9,247 records.
All 4,920 existing recent ratings, reasons, and provenance remain unchanged.
The build replays recorded judgments and checks exact saved source matches.
The build does not infer magnitude from earlier scope labels.

Earlier primary_scope and title_stage fields remain unassessed for 2021–2024.
Existing release-type and enhancement labels are retained. The new magnitude
scale describes changes to AWS products themselves. 

Earlier magnitude/ files
measure customer consequences and are superseded. Do not use those scripts
to regenerate the current measure. Older DuckDB columns remain for history.

Historical service tags are unknown on these rows:
2021: 108 of 2,084; 2022: 50 of 2,103;
2023: 48 of 2,715; 2024: 40 of 2,345.
Account for missing tags and overlapping services in service comparisons.

Read the charts

product_change/annual.svg uses matched.csv: 1 January–28 October each year.

product_change/annual_full.svg uses annual.csv: full years, except 2026.

product_change/monthly.svg uses monthly.csv: October 2026 is partial.

product_change/service_matched.csv compares services over matched periods.

product_change/matched.svg retains the earlier 2025–2026 comparison.

The six-year monthly share view uses all filtered announcements, including
NA (outside scale). In-scale totals include U (needs review) and exclude NA.
Pure pricing, lifecycle, regional, and non-product announcements are outside
the scale. 

Billing functionality is assessed normally. Service tags and
enhancement facets can overlap. Counts measure announcements, not unique launches.

Audit and reproduction

The historical_review directory contains frozen sources, initial decisions,
independent readings, references, corrections, and metrics for its fresh audit.
The source_review directory contains the earlier recent review evidence.
product_change/review_report.json records that earlier review's source hashes,
category transitions, and agreement. Historical and subtype methods are in
historical-methods.md and subtype-methods.md in the extracted archive.

The recent fresh_accuracy audit scores its frozen predictions. The audit results do
not score the combined export. Historical_review preserves the earlier recent
exports as baseline_2025_2026.csv and baseline_2025_2026.json.

Stop the server before rebuilding. Run these commands from the extracted folder:

.venv/bin/python product_change/historical_audit.py score
.venv/bin/python product_change/build.py
.venv/bin/python product_change/charts.py
.venv/bin/python product_change/verify.py
.venv/bin/python product_change/package.py

These steps replay the saved decisions. They do not rerun an AI classifier.
See REPRODUCING.md for the expected results and distribution instructions.

Substantive trend analysis

substantive_trends/REPORT.md compares refinements and larger changes with
new capabilities and larger additions. The folder includes charts, trend data, recent velocity comparisons, and
reproducible analysis.
Read its limits before attributing growth to individual services.
