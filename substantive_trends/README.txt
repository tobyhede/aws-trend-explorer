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
