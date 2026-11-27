# Read the AWS announcement data

Release: 27 November 2026. Use `product_change/announcements.csv` or `product_change/announcements.json` for the current classification. Both exports contain 22,588 records, one for each collected announcement from 1 January 2010 to 28 October 2026.

The public dataset, `product_change/public/aws-announcements-2026-11-27.parquet`, contains the same records with nine of these fields: every field below except `primary_scope`, `title_stage`, and `announcement_text`.

## Exported fields

Each row represents one collected announcement. `source_url` identifies a record in this release. CSV text fields can contain commas and line breaks; use a CSV reader instead of splitting lines.

| Field | Meaning |
| --- | --- |
| `announcement_date` | Publication date, formatted as YYYY-MM-DD. |
| `title` | Saved announcement title. |
| `service` | Service tags separated by `; `. `unknown` means no service tag is available. |
| `release_type` | Retained release-type label from the earlier classification; empty before 2021. |
| `primary_scope` | Earlier scope label; unassessed before 2025. |
| `enhancement_facets` | Retained enhancement labels, separated by `|`; an announcement can have several. Empty before 2021. |
| `product_change_level` | Current magnitude code, defined below. Treat this as text. |
| `product_change_reason` | Explanation based on the announcement and recorded review. |
| `product_change_basis` | Provenance identifying the classification or adjudication. |
| `title_stage` | Earlier stage label; unassessed before 2025. |
| `source_url` | Official source URL for the announcement. |
| `announcement_text` | Saved source text used for classification. |

Missing values use empty CSV fields or JSON null values. `NA` and `U` are explicit decisions, not missing values. DuckDB contains additional provenance and older analysis columns. Use `product_change_level` for the current magnitude measure.

## Magnitude categories

The scale describes the announced product change, not its consequences for a customer.

| Code | Category | Decision rule |
| --- | --- | --- |
| `1` | Parameter change | A limit, default, performance characteristic, or supported catalogue value changes. |
| `2` | Capability refinement | Controls, options, compatibility, or targets extend an existing operation. |
| `3` | New capability | A distinct new operation or interface appears within an existing product. |
| `4` | Major product expansion | A substantial subsystem or new execution, operating, or programming model appears. |
| `5` | New product | AWS positions a distinct offering that customers can adopt. Billing is supporting evidence. |
| `U` | Needs review | The evidence does not establish the change sufficiently. |
| `NA` | Outside scale | Pure geographic, price-only, compliance, educational, or lifecycle announcements. |

Mixed announcements receive the highest substantive level supported by their text. Routine hardware, runtime, and model catalogue additions are generally level 1. An additional integration target is generally level 2. A first integration that adds a distinct capability can be level 3.

General availability alone does not imply a new product. Assess explicit additions separately; an unclear addition can remain `U`. Billing functionality remains eligible even though pure price changes are outside scale.

The levels are ordered categories, not arithmetic weights. Do not multiply counts by the level number to estimate effort or value. A service-limit facet remains separate from a performance facet, even when both changes receive magnitude level 1.

## Chart periods and totals

The files under `product_change/` use these comparisons:

| Data file | Period | Related chart |
| --- | --- | --- |
| `matched.csv` | 1 January–28 October in each year | `annual.svg` |
| `annual.csv` | Calendar years; 2026 ends on 28 October | `annual_full.svg` |
| `monthly.csv` | Calendar months; October 2026 ends on day 28 | `monthly.svg` |
| `service_matched.csv` | Services over the same matched annual periods | Service comparison data |

`matched.svg` keeps the earlier two-year comparison. The annual chart covering 2010–2026 is `annual.svg`.

The monthly share view divides each category count by all filtered announcements. That denominator includes `NA` and `U`. In-scale annual totals exclude `NA` but include `U`. Year-on-year change compares adjacent matched periods, using the previous year's total as the denominator.

Service tags overlap. Count a multi-service announcement once for each associated service, but once in the overall corpus. Unknown service tags and differences in collection coverage can affect comparisons.

Most announcements from 2010–2014 have no service tag: between 77% and 98% of each year's records are `unknown`. From 2015 the share is at most 17% in every year. A per-service count that starts before 2015 therefore measures tagging as well as output.

## Periods and labelling passes

The explorer and `substantive_trends/periods.py` group years into three periods: pre-COVID (2010–2019), COVID (2020–2021) and post-COVID (2022–2026). These are analysis groupings, not part of the rubric.

Three labelling passes produced the levels, and the passes do not line up with the periods:

| Years | Records | Pass | Evidence |
| --- | ---: | --- | --- |
| 2010–2020 | 8,421 | Two AI readers on every record; a third reading settles each disagreement | `product_change/early_review/` |
| 2021–2024 | 9,247 | One AI reader per record, with targeted review | `product_change/historical_review/` |
| 2025–2026 | 4,920 | One AI reader per record | `product_change/source_review/` |

`product_change_basis` names the pass for each record. The 2010–2020 pass rates higher than the earlier passes. A bridge sample of 400 records from 2021–2026 was read again under the 2010–2020 protocol. Level 3 was 14.0% of the recorded labels and 20.8% of the new ones. A difference between periods smaller than that is not a finding.

## Interpret trends with the audit

Announcement volume measures publication activity. Repeated stages or regional releases can describe the same underlying feature. Seasonal publication patterns and partial periods also affect apparent velocity.

The [release notes](RELEASE_NOTES.md) explain the three audits, the bridge sample, and their limits. Rare-category trends remain provisional, and level 4 and level 5 trends above all. The older release-type, facet, and scope audits do not establish accuracy for this magnitude rubric.
