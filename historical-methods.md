# AWS announcement history

Open review.html to search all 14,167 announcements by title, source service tag, primary type or enhancement facet. The interval is January 1, 2021 through October 28, 2026 inclusive. Each row has one official AWS announcement URL. Three rows link to a contemporaneous AWS News Blog article for their summary because the announcement body itself contained only “NO CONTENT”. The CSV and JSON include text provenance.

## How to interpret the counts

annual.csv supplies both the observed interval in each year and a comparable January 1–October 28 window. The 2026 observed interval is partial. Rolling weekly publication velocity is the preceding 91 calendar days divided by 13. Daily zeros count toward the denominator. monthly.csv and monthly_velocity.png include the final partial month. Service counts use distinct AWS tags per announcement and can overlap. The service chart omits unknown, GovCloud and the broad machine-learning tag; service_years.csv retains all source tags. Missing service tags affect 257 records in the 2026 matched period and 37 in 2025.

Classification retained the latest 4,275 matched-period decisions and extended primary labels to 9,892 records. Primary labels are mutually exclusive. The historical classifier applies URL-specific reviewed decisions and textual rules, defaulting to enhancement. This can hide rarer product milestones, lifecycle events and releases. primary_prior.json preserves previously accepted decisions. A blind independent reader classified 30 records in each of the five extension years (the 2025 extension covers October 29–December 31 only). Before reconciling the readings, the primary assignments matched 137 of 150 random-sample labels and 37 of 40 separately targeted launch-boundary labels. These are agent comparisons. Equal yearly sample sizes give different sampling fractions, and the targeted check deliberately overrepresents difficult cases. audit_results.csv preserves the individual results.

Enhancement facets overlap. The historical pass found at least one facet on 3,918 of 7,386 historical enhancements; 3,468 have an empty facet field. Prior two-year enhancements received more extensive review. Treat historic facet counts as provisional detected labels, particularly for the performance and integration series. Consult facet_notes.md for per-label checks. The legacy_category field reproduces the earlier five-way product/major/minor/maintenance/unknown heuristic. Its earlier holdout had 55 agreements in 100 diagnostically sampled rows. It is included for compatibility; this report uses the reviewed ontology.

The two official inventories reconciled for the earlier collection are the AWS directory API and English marketing sitemap. Coverage across 2021–2024 was checked further against 151 announcements linked in 13 AWS editorial roundups; all matched, including one truncated link resolved using its context. This purposive check covers only linked announcements. The sitemap snapshot supplies no independent historical inventory for those four years. Deleted or unindexed posts may remain absent. distinct_text_check.csv quantifies the sensitivity of the headline counts to dropping repeat bodies across URLs.

## Rebuild

The archive includes the matched-period source snapshot, URL-bound prior decisions, source readings and classifiers. With Python, DuckDB and matplotlib installed, run these commands from the archive root.

    python historical/primary.py
    python historical/facets.py
    python historical/analyze.py
    python historical/explorer.py

The new DuckDB contains announcements, annual, monthly, rolling_13_weeks, primary_annual, service_years, facet_years and audit_results. The companion source audit archive contains the raw page snapshots and collection-stage code. Coverage and audit notes are packaged alongside the data.
