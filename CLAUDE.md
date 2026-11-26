# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A released data bundle plus a local viewer: 14,167 AWS "What's New" announcements (1 January 2021 – 28 October 2026), each with an AI-assigned product-change magnitude, the saved review evidence behind those labels, and the scripts that replay that evidence into exports and charts. It is distributed as `aws_trend_explorer.zip`; `README.txt` is the recipient-facing entry point.

There is one explorer page, `hosted/site/`. Published, it is the hosted explorer: a public static site that presents the release from the public dataset, which is the records without saved announcement text. Run through `serve.py`, the same page is the local explorer, and it also shows each record's saved announcement text (ADR 0003). `GLOSSARY.md` fixes the terms release bundle, public dataset, local explorer and hosted explorer; `docs/adr/` records why the public dataset omits text, why the explorer counts in JavaScript, and why there is one page.

There is no test suite, linter, or build system. `product_change/verify.py` is the correctness check for the release, and `hosted/check.mjs` is the check for the hosted explorer's counting.

## Commands

All commands run from the repository root. Scripts under `product_change/` import each other as siblings (`from review import ...`), so invoke them by path as shown rather than as modules.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt   # only dependency: duckdb==1.5.6
.venv/bin/python serve.py                             # http://127.0.0.1:8765; --port N, --database PATH
```

Rebuild pipeline, in this order. Stop `serve.py` first: the build opens `announcements.duckdb` read-write.

```sh
.venv/bin/python product_change/historical_audit.py score   # score frozen predictions against saved references
.venv/bin/python product_change/build.py                    # replay decisions into DuckDB, write announcements.csv/json and matched.csv
.venv/bin/python product_change/public_dataset.py           # write the public dataset (Parquet, nine fields, no announcement text)
.venv/bin/python product_change/charts.py                   # SVG charts and aggregate CSVs
.venv/bin/python product_change/verify.py                   # integrated check
.venv/bin/python product_change/package.py                  # writes ../aws_trend_explorer.zip, replacing any existing one
```

`verify.py` succeeds with: `Verified source coverage, unchanged recent ratings, chart cells, service tags and all 14,167 CSV/JSON records.`

Substantive trend analysis needs matplotlib as well:

```sh
.venv/bin/python -m pip install -r substantive_trends/requirements.txt
.venv/bin/python substantive_trends/recalculate.py
```

Hosted explorer, development only (needs Node 22 or later; no package install):

```sh
.venv/bin/python hosted/pages.py                 # regenerate the supporting pages in hosted/site/
node hosted/check.mjs                            # counting module against matched.csv, monthly.csv, service_matched.csv and serve.py summaries
.venv/bin/python hosted/check_site.py            # upload set: no announcement text, no third-party requests, pages current
python3 -m http.server -d hosted/site 8766       # view it; any static server works
PAGES_PROJECT=<name> hosted/publish.sh           # manual publish to Cloudflare Pages; run only when the maintainer asks
```

`REPRODUCING.md` has a snippet that compares rebuilt outputs with the SHA-256 hashes in `release/reproduction.json`.

## Rules that are easy to break

- The build replays recorded judgments. It never calls a model and never infers a level from other labels. `build.py:classify` is a plain dictionary lookup, and a record with no decision is an error, not a fallback.
- Do not run `historical_audit.py prepare` or `freeze`. They regenerate review inputs and frozen references, which destroys the audit's independence. Only `score` is part of reproduction.
- Do not run anything under `magnitude/` to produce current results. That measure (customer consequences, architecture change) is retired; see `magnitude/SUPERSEDED.txt`. `scope/` is likewise earlier-stage evidence.
- The 4,920 recent (2025–2026) ratings, reasons, and provenance must stay unchanged. `historical.py:verify_recent_baseline` and `verify.py` enforce this.
- Corrections go into the recorded evidence (`product_change/audit_corrections.json`, or the `REVIEWED` map in `build.py`), keeping the original prediction and audit reference. Then rerun build, charts, and verify. A new release also needs the release date, audit evidence, and `release/reproduction.json` hashes updated.
- This repository stays private. It contains saved announcement text, which the AWS Site Terms do not let us republish (ADR 0001). Only `hosted/site/` is ever published, and only through `hosted/publish.sh`. Never add `announcement_text`, an excerpt of it, or an index built from it to `hosted/site/` or to the public dataset. The checks are a backstop, not a licence: `verify.py` fails on a text field or a whole saved text in any public field, and `hosted/check_site.py` fails on a run of eight copied words in a page or script, but neither detects a short excerpt written into a reason.
- There is one explorer page. Change `hosted/site/` and both the published site and the local explorer change; never build a second page. Anything that needs saved announcement text must be read from `serve.py` at run time and shown only when the page carries `data-local`, which `serve.py` adds and the published files never have. The root `index.html`, `scope.js`, `magnitude.js` and `product_trends.js` are the earlier local page: `serve.py` no longer serves `index.html`, and they are kept only until the maintainer confirms their removal.
- Do not edit `release/reproduction.json` or `release/documentation_checks.json` between releases. They record the 25 November 2026 release. `REPRODUCING.md` has changed since, so its recorded documentation hash is stale, and the public dataset has no recorded hash yet; refresh both at the next release. `README.txt` does not yet mention the public dataset or its build step.
- The record count 14,167, the date bounds, and the 28 October cutoff are hard-coded in several places: `serve.py` (`FIRST`, `LAST`, `'10-28'` in SQL), `build.py` (assertion), `product_trends.js` (year and month loops, `2026-10` ending on day 28), and all four documentation files. Changing the corpus means changing all of them. The hosted explorer's page code reads its release date, first date and cutoff from `hosted/site/release.js` alone. A new release also changes: the release date and cutoff in `product_change/public_dataset.py` (file name and metadata; `hosted/check.mjs` fails if they disagree with `release.js`), the static download link in `hosted/site/index.html` (`hosted/check_site.py` fails if it is stale), the record count 14,167 asserted in `public_dataset.py`, `verify.py` and `hosted/check.mjs`, and the month count and comparison years asserted in `hosted/check.mjs`.

## Architecture

**Data flow.** `announcements.duckdb` is both input and output. `build.py` reads the `announcements` table, loads recent decisions through `review.py` (from `product_change/source_review/`) and historical decisions through `historical.py` (from `product_change/historical_review/`), writes them to a `product_change_decisions` table, copies them onto three `product_change_*` columns of `announcements`, and exports CSV and JSON. `charts.py` and `history_charts.py` derive the aggregate CSVs and SVGs. `source_url` is the record key throughout.

**Evidence directories.** `source_review/`, `historical_review/`, and `fresh_accuracy/` hold batches, per-reader ratings (`ratings*.tsv`), frozen references, adjudications, and metrics. These are inputs to the build and the audit record. Treat them as append-only evidence, not generated output. `fresh_accuracy/` scores its own earlier frozen snapshot, not the combined export.

**Current versus legacy columns.** `product_change_level`, `product_change_reason`, and `product_change_basis` are the current measure. `magnitude`, `affected_workload`, `magnitude_reason`, `magnitude_review`, and `legacy_category` are retired but kept for history. `primary_scope` and `title_stage` are unassessed (null) for 2021–2024; `release_type` and `enhancement_facets` are retained earlier labels. Multi-valued fields use different separators: `service` uses `'; '` and `enhancement_facets` uses `'|'`.

**Viewer.** `serve.py` is a single-file, read-only `http.server` bound to 127.0.0.1. It serves the explorer page from `hosted/site/` (any file under that folder, with `data-local` added to the page), `/api/text` for one record's saved announcement text, and a fixed whitelist of audit and data paths (the `pages` dictionary; a new one needs an entry there), plus `/api/options`, `/api/summary` (LRU-cached per filter set), `/api/rows` (25 per page), and `/export.csv`. Retired architecture and magnitude audit routes deliberately return 410 with `product_change/retired.html`. The summary and row routes are no longer used by the page; `hosted/check.mjs` still compares the page's counting with them. The earlier local page (`index.html` with `scope.js`, `magnitude.js` and `product_trends.js`) is unserved. `architecture.js` is not loaded by `index.html`.

**Public dataset.** `product_change/public_dataset.py` selects nine fields from `announcements` into `product_change/public/aws-announcements-<release date>.parquet` (Snappy, which the vendored reader decodes without extra code) and copies the file to `hosted/site/data/` when `hosted/` exists. The copy in `product_change/public/` goes into the release bundle; `package.py` includes `hosted/site/` (the explorer page) and leaves the rest of `hosted/` out. Dated files from earlier releases stay in `hosted/site/data/` so their addresses keep working.

**Hosted explorer.** `hosted/site/` is exactly what is uploaded: plain HTML, CSS and JavaScript modules, no bundler, no package install, no CDN. `counting.js` holds all filtering and counting, including the share denominator, and touches no page elements; `app.js` only draws; `release.js` is the one place for the release date and cutoff; `vendor/hyparquet/` is a pinned copy of hyparquet 1.33.2. The page fetches the Parquet file once and counts in memory. Search covers title and reason only, so it can return fewer records than the local explorer. `method.html`, `historical-audit.html`, `fresh-audit.html`, `data-guide.html` and `release-notes.html` in `hosted/site/` are generated by `hosted/pages.py` from the release's reports and from `hosted/pages/`; edit the sources, not the outputs. The 120-record review (`review.html`) and raw review evidence are not published.

**Scope filter quirk.** Because `primary_scope` exists only for 2025–2026, selecting a scope filter in `serve.py:overview` shifts the series start to 2025.

## Semantics to preserve in code and prose

`DATA_GUIDE.md` is the authority for field meanings and the rubric. Points that affect calculations:

- Levels `1`–`5`, `U` (needs review), and `NA` (outside scale) are text, and are ordered categories, not weights. Never multiply counts by level.
- `U` and `NA` are explicit decisions, not missing values. In-scale totals include `U` and exclude `NA`. The monthly share view divides by all filtered announcements, including both.
- Year comparisons use the matched period, 1 January – 28 October, in every year. 2026 and October 2026 are partial.
- Service tags overlap; a multi-service announcement counts once per service, so service totals must not be summed. `unknown` marks a missing tag.
- In `substantive_trends/`, "broad" means levels 2–5 and "strict" means levels 3–5. These are analysis thresholds, not part of the rubric.

Documentation in this bundle states its limits carefully: labels are AI judgments, corpus coverage is not proven exhaustive, and level 4 and 5 trends are provisional. Keep that hedging when editing docs or adding analysis; a successful rebuild shows reproducibility, not accuracy.

`historical-methods.md` and `subtype-methods.md` describe earlier pipelines whose scripts (`historical/`, `subtype_validation/`) are not in this bundle. Their rebuild commands will not run here.

## Agent skills

### Issue tracker

Issues live in this repository's GitHub Issues, through the `gh` CLI. The earlier hosted explorer spec and issues stay as files under `.scratch/hosted-explorer/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repository root. See `docs/agents/domain.md`.
