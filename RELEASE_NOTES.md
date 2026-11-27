# AWS announcement explorer: 27 November 2026

This release extends the corpus back to 2010 and gives every 2010–2020 announcement a product-change magnitude decision. The release contains 22,588 announcements from 1 January 2010 through 28 October 2026.

Classification describes the size of the announced product change itself. The categories do not measure customer consequences, engineering effort, or business value. AI readers produced the classifications and the audit references.

The 2010–2020 labels come from a different review protocol from the 2021–2026 labels, and that protocol rates higher. Read any comparison across 2020 against the bridge sample results below.

## Changes in this release

- Added 8,421 announcements from 2010–2020, collected from the AWS directory API on 27 November 2026.
- Labelled every 2010–2020 announcement with two independent AI readers, and a third reading for each of the 303 disagreements.
- Added a blind audit of 300 hidden-sample records from 2010–2020.
- Added a bridge sample: 400 records from 2021–2026 read again under the 2010–2020 protocol, to measure how differently the two protocols rate.
- Drew 40 records at levels 4 and 5 for a check by the maintainer.
- Kept all 9,247 ratings for 2021–2024 and all 4,920 ratings for 2025–2026 as recorded.
- Rebuilt the CSV, JSON, DuckDB and chart exports and the public dataset, `product_change/public/aws-announcements-2026-11-27.parquet`, to cover 2010–2026.
- Added a comparison of three periods: pre-COVID (2010–2019), COVID (2020–2021) and post-COVID (2022–2026).
- Extended the explorer page to 2010, with the periods marked and a caveat for records without a service tag.

The annual comparison uses 1 January–28 October in every year. The monthly chart includes full earlier years and ends on 28 October 2026.

## Collected records by year

Every collected record has a magnitude decision, including explicit needs-review and outside-scale decisions.

| Year | Announcements | Labelling pass |
| --- | ---: | --- |
| 2010 | 66 | 2010–2020 |
| 2011 | 82 | 2010–2020 |
| 2012 | 91 | 2010–2020 |
| 2013 | 185 | 2010–2020 |
| 2014 | 295 | 2010–2020 |
| 2015 | 452 | 2010–2020 |
| 2016 | 640 | 2010–2020 |
| 2017 | 1,023 | 2010–2020 |
| 2018 | 1,433 | 2010–2020 |
| 2019 | 1,860 | 2010–2020 |
| 2020 | 2,294 | 2010–2020 |
| 2021 | 2,084 | 2021–2024 |
| 2022 | 2,103 | 2021–2024 |
| 2023 | 2,715 | 2021–2024 |
| 2024 | 2,345 | 2021–2024 |
| 2025 | 2,663 | 2025–2026 |
| 2026, through 28 October | 2,257 | 2025–2026 |
| Total | 22,588 | |

## How the 2010–2020 records were collected

The AWS directory API listed 8,423 records under the 2010–2020 year tags on 27 November 2026. Two of them are dated 2026. Those two were set aside, leaving 8,421 records. The saved responses and their hashes are in `product_change/early_snapshot/`.

Coverage means what the API listed on that date. To check it, each year was compared with an archived copy of that year's announcement index page:

- The archived pages link 79 announcements that the API no longer lists. They are reported, not added.
- 58 of the 79 are from 2012, mostly from late September onward. The API lists 91 posts for 2012; a March 2013 capture links 146.
- Every other checked year has between 0 and 5 absent links.
- 2017 is unchecked, because the archive holds no capture of its index page from the right months.
- The 2010, 2011, and 2016 captures were taken before the end of the year. Posts from the last weeks of those years cannot appear in them.

The [coverage report](product_change/early_snapshot/coverage.txt) lists every absent link.

## 2010–2020 labelling and audit results

Labelling ran as headless Claude Code sessions, each one fresh, with no tools and no project instructions. Two readers on `claude-fable-5-2` rated every record without seeing each other's ratings. A third reading on the same model settled each disagreement. Every request, reply, and model name is saved in `product_change/early_review/`.

A hidden sample of 300 records was drawn before any reading. One blind reading by a different model, `claude-opus-5-5`, gives the audit reference. The final labels agree with that reference on 272 of the 300 records. Weighted to each year's share of the records, agreement is 90.2%, with a 95% interval of 86.1–94.3%. This interval describes sample uncertainty; it does not account for bias the AI readers share.

Agreement at level 4 is weak. The labels and the reference agree on 3 records, out of 7 labelled level 4 and 5 given level 4 by the reference. The earlier audits found the same weakness. The [scores](product_change/early_review/scores.txt) give the results for each year and each level.

## Bridge sample results

The bridge sample holds 200 records from each earlier pass. The readers saw the announcement only, not the recorded label. The new readings never change a recorded label.

| Earlier pass | Agree with recorded label | Agreement |
| --- | ---: | ---: |
| 2025–2026 | 170 of 200 | 85.0% |
| 2021–2024 | 153 of 200 | 76.5% |
| Both | 323 of 400 | 80.8% |

The disagreements mostly go one way. 35 records labelled level 2 became level 3 under the new protocol, and 7 went from level 3 to level 2. Level 3 is 14.0% of the recorded labels and 20.8% of the new labels.

So the 2010–2020 labels probably rate higher than the 2021–2026 labels would for the same announcements. A difference between periods smaller than this drift is not a finding. The bridge holds only 2021–2026 records, so it cannot detect drift specific to older texts. That includes readers rating an early launch by what the product later became.

## Period comparison

`substantive_trends/periods.py` computes the level shares for each period, and `substantive_trends/PERIODS_REPORT.md` is an AI reading of those tables. The maintainer has not endorsed it.

Counting 1 January to 28 October in each year, level 3 is 17.4% of pre-COVID announcements and 12.5% of post-COVID announcements. That fall is no larger than the bridge drift, and it runs in the direction the drift predicts. The report therefore does not treat it as a real change. Announcement volume and the counts at levels 2–5 and 3–5 are higher after 2020 than before.

## Maintainer's check of level 4 and level 5 records

40 records were drawn from the 459 records of 2010–2020 at level 4 or level 5. The draw used a saved seed, and the records are listed in `product_change/early_review/human_check/records.md`. The maintainer's readings have not been recorded in this release. When they are, `early_human.py report` counts them apart from the AI agreement figures.

## 2021–2024 audit results

The fresh sample contains 200 records from 2021–2024, selected before classification. Two independent readers assessed every sampled announcement without seeing the production labels or each other's decisions. A third reader assessed disagreements, low-confidence cases, and selected agreements.

Initial classifications agreed with the final reference on 177 records, or 88.5%. The Wilson 95% interval is 83.3%–92.2%. Among reference records assigned levels 1–5, agreement was 123 of 145, or 84.8%.

All 233 initial level-4 and level-5 decisions for 2021–2024 received a second reading. This targeted review checks existing high ratings; it cannot find every large change given a lower rating. The random sample contained two reference level-4 records, and the initial classifications missed both. It contained no reference level-5 records.

The [historical audit report](product_change/historical_review/report.html) gives the category results, and the [audit metrics](product_change/historical_review/metrics.json) contain the exact calculations.

## 2025–2026 audit results

A separate fresh sample of 200 records from 2025–2026 was scored against a blind, adjudicated AI reference. 173 classifications matched, or 86.5%, with a Wilson 95% interval of 81.1%–90.6%. Its findings were not applied as corrections.

## Checks completed

- `verify.py` confirms unique source URLs and a magnitude decision for every record.
- It confirms that every 2010–2020 decision replays from its saved readings, and that the 2021–2026 decisions are unchanged.
- It checks the exports, chart totals, service counts, and chart drill-down results.
- It confirms that the public dataset holds all 22,588 records, agrees with the database, and contains no announcement text.
- `early_checks.py` runs 26 offline checks of collection, labelling, scoring, sampling and the period tables, with canned replies.
- `hosted/check.mjs` confirms that the explorer page's counts equal the verified annual, monthly, and per-service counts.

The [reproduction evidence](release/reproduction.json) records the hashes of the rebuilt outputs. The [verification report](product_change/verification_report.txt) records the integrated check result. The release was tested with Python 3.13.7 and DuckDB 1.5.6 on macOS. Other operating systems have not been tested.

## Limits that remain

- All labels are AI judgments. The audits measure agreement with AI references, not accuracy validated by people.
- Classification covers the collected corpus. Collection coverage has not been proven exhaustive. The 2012 records are known to be incomplete. 2017 coverage is unchecked.
- The 2010–2020 protocol rates higher than the 2021–2026 passes. Comparisons across 2020 mix any real change with that difference.
- Level 4 and level 5 trends are provisional. Agreement at level 4 is weak in every audit. The maintainer's check is not yet recorded.
- The early years are small: 66 announcements in 2010 and 82 in 2011. Shares from such small counts change widely from year to year.
- 232 records are marked needs review: 6 from 2010–2020, 204 from 2021–2024 and 22 from 2025–2026.
- Service tags are unknown on 2,106 records. Between 77% and 98% of each year's records from 2010–2014 have no tag. Service tags can overlap, so service totals must not be added together.
- The `primary_scope` and `title_stage` fields are unassessed before 2025. The release-type and enhancement labels are empty before 2021.
- Announcement counts are not counts of unique features or products. Preview, general availability, and regional rollout can produce separate announcements.
- The release contains no publications after 28 October 2026. The release date is not the collection cutoff.

Prioritise broader independent review of rare categories and of collection coverage before making strong claims about category trends. Review this documentation whenever the corpus, rubric, or audit reference changes.
