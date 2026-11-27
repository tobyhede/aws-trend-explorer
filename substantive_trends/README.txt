Substantive trend analysis, calculated 25 November 2026

Read REPORT.md for definitions, findings, and limits. Open trends.svg or
trends.png for the charts. The CSV files contain annual, monthly, 90-day,
and raw service-tag comparisons. results.json records definitions and exact
calculations, including the source export hash.

From the extracted explorer folder, install the chart dependency and run:

.venv/bin/python -m pip install -r substantive_trends/requirements.txt
.venv/bin/python substantive_trends/recalculate.py

The script reads product_change/announcements.csv and checks its annual
aggregations against product_change/matched.csv. The script writes CSV,
JSON, PNG, and SVG files in this folder. REPORT.md is the written interpretation
of the released results; update it if the input data changes.

Broad means levels 2–5. Strict means levels 3–5. Neither includes unresolved
records, parameter changes, or outside-scale announcements. The thresholds
are analytical choices, not changes to the agreed classification rubric.

Period comparison (periods.py)
periods.py compares substantive output across the pre-COVID (2010–2019), COVID (2020–2021) and post-COVID (2022–2026) periods, with 2015–2019 as a sensitivity window, from the built corpus. It needs only DuckDB. Every figure uses 1 January – 28 October in every year.
- periods.txt and periods.json: the annual series of announcements, levels 3–5 and levels 2–5; the median year-on-year change of each per period (changes ending in the window's years; a zero base is left out); and the share at each level per period with Wilson intervals, NA and U as their own rows. Audit agreement, bridge drift, the archive coverage gap and the labelling protocol behind each period print beside the shares.
- PERIODS_REPORT.md: an interpretation written by a Claude Code agent from periods.txt alone, kept as evidence and marked as an AI reading. periods.py fails if the report holds a number that is not in the tables.
- There is no average level, weighted score, counterfactual or service breakdown.

Run from the repository root: .venv/bin/python substantive_trends/periods.py
