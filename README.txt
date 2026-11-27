AWS announcement explorer
Release: 27 November 2026

Explore 22,588 collected AWS announcements from 1 January 2010 through 28 October 2026. Every record has a product-change magnitude decision. The classifications and the audit references are AI judgments. Collection coverage has not been proven exhaustive.

Start the explorer

Extract aws_trend_explorer.zip into its own folder. Open a terminal in that folder. The following commands are for macOS or Linux:

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python serve.py

Open http://127.0.0.1:8765 in your browser. Keep the terminal running. Press Control-C in that terminal to stop the server. If the port is already in use, run .venv/bin/python serve.py --port 8766 and open port 8766 instead.

The server listens on your computer only. The URL is not a shared website.

The release was tested on macOS with Python 3.13.7 and DuckDB 1.5.6. Installing the dependency needs internet access. Browsing the bundled data and rebuilding the exports do not need an AWS account or access to an AI model. Other operating systems have not been tested.

Find the data and documentation

RELEASE_NOTES.md explains the changes, audit results, checks, and remaining gaps.
DATA_GUIDE.md defines the exported fields, magnitude levels, and chart totals.
REPRODUCING.md explains how to rebuild, check, and share the release.

announcements.duckdb contains the announcements table.

product_change/announcements.csv and announcements.json contain all records, including source URLs, saved announcement text, magnitude, reason, and basis.

product_change/public/aws-announcements-2026-11-27.parquet is the public dataset: every record with nine fields and no saved announcement text. It is the only file in this bundle prepared for publication.

product_change/method.html explains the rubric and gives reviewed examples.

product_change/early_review/ contains the evidence and scores for the 2010–2020 labels: the audit, the bridge sample, and the maintainer's check.

product_change/early_snapshot/ contains the saved AWS directory responses for 2010–2020 and the coverage check against archived index pages.

product_change/historical_review/report.html contains the 2021–2024 audit.

product_change/fresh_accuracy contains the separate 2025–2026 fresh-sample audit.

product_change/review.html contains the earlier 120-record audit of the 2025–2026 labels.

How the records were labelled

Three passes labelled the corpus, each with its own evidence.

- 2010–2020: 8,421 records. Two AI readers rated every record, and a third reading settled each of the 303 disagreements.
- 2021–2024: 9,247 records. One AI reader per record, with targeted review.
- 2025–2026: 4,920 records. One AI reader per record. These ratings, reasons, and provenance are unchanged from the earlier releases.

The 2010–2020 pass used a different protocol, so a bridge sample of 400 already-labelled 2021–2026 records was read again under it. That protocol rates higher: on the bridge sample, level 3 is 14.0% of the recorded labels and 20.8% of the new ones. Read any comparison between 2010–2020 and later years against that difference. The recorded 2021–2026 labels were not changed.

The build replays recorded judgments and checks exact saved source matches. It never calls an AI model, and it does not infer magnitude from earlier scope labels.

The earlier primary_scope and title_stage fields are unassessed before 2025. The earlier release-type and enhancement labels are kept. The magnitude scale describes changes to the AWS products themselves.

The earlier magnitude/ files measure customer consequences and are superseded. Do not use those scripts to regenerate the current measure. Older DuckDB columns remain for history.

Service tags are missing on most early records

A record with no service tag shows as unknown. Most 2010–2014 records have no tag:

2010: 65 of 66; 2011: 79 of 82; 2012: 88 of 91; 2013: 182 of 185; 2014: 227 of 295.

From 2015, between 40 and 273 records a year are untagged. Across the release, 2,106 records are untagged. A service comparison that reaches back before 2015 measures tagging as much as output. Service tags also overlap, so service totals must not be added together.

Read the charts

product_change/annual.svg uses matched.csv: 1 January–28 October each year.

product_change/annual_full.svg uses annual.csv: full years, except 2026.

product_change/monthly.svg uses monthly.csv: October 2026 is partial.

product_change/service_matched.csv compares services over matched periods.

product_change/matched.svg keeps the earlier 2025–2026 comparison.

The monthly share view divides by all filtered announcements, including NA (outside scale). In-scale totals include U (needs review) and exclude NA. Pure pricing, lifecycle, regional, and non-product announcements are outside the scale.

Billing functionality is assessed normally. Service tags and enhancement facets can overlap. Counts measure announcements, not unique launches.

Audit and reproduction

Each pass has an audit that compares its labels with an independent AI reference. Agreement between AI readings is not accuracy:

- 2010–2020: 90.2% agreement, weighted to each year's records (95% interval 86.1–94.3%).
- 2021–2024: 88.5% agreement (Wilson 95% interval 83.3–92.2%).
- 2025–2026: 86.5% agreement on a separate fresh sample (Wilson 95% interval 81.1–90.6%).

RELEASE_NOTES.md gives the details and the limits of each audit.

Stop the server before rebuilding. Run these commands from the extracted folder:

.venv/bin/python product_change/historical_audit.py score
.venv/bin/python product_change/early_score.py
.venv/bin/python product_change/build.py
.venv/bin/python product_change/public_dataset.py
.venv/bin/python product_change/charts.py
.venv/bin/python product_change/verify.py
.venv/bin/python product_change/package.py

These steps replay the saved decisions. They do not run an AI classifier again. See REPRODUCING.md for the expected results, the offline checks of the 2010–2020 evidence, and how to share the release.

Substantive trend analysis

substantive_trends/REPORT.md compares refinements and larger changes with new capabilities and larger additions. The folder includes charts, trend data, comparisons of recent velocity and the analysis code. Read its limits before you attribute growth to individual services.

substantive_trends/PERIODS_REPORT.md compares the pre-COVID (2010–2019), COVID (2020–2021) and post-COVID (2022–2026) periods. It is an AI reading of the computed tables, not a finding the maintainer has endorsed. Its main limit is the reader difference that the bridge sample measures.
