# Reproduce and share the AWS explorer release

Release: 27 November 2026. The archive contains data, saved review evidence, analysis code, and charts. Reproduction replays recorded judgments; it does not ask an AI model to classify the records again.

## Run the included data

Follow `README.txt` to install the pinned dependency and start the local explorer. The tested environment uses Python 3.13.7 and DuckDB 1.5.6. If you only need static figures, open the SVG charts directly in a browser.

## Rebuild the outputs

Work in a copy of the extracted archive. Stop the explorer before changing its database. Run these commands from the extracted folder after installing its requirements:

```sh
.venv/bin/python product_change/historical_audit.py score
.venv/bin/python product_change/early_score.py
.venv/bin/python product_change/build.py
.venv/bin/python product_change/public_dataset.py
.venv/bin/python product_change/charts.py
.venv/bin/python product_change/verify.py
```

Each command does one step:

1. `historical_audit.py score` scores the frozen 2021–2024 predictions against their saved references.
2. `early_score.py` scores the 2010–2020 labels against their audit reference, and the bridge sample against the recorded labels. It writes `audit_metrics.json`, `bridge_metrics.json`, and `scores.txt` in `product_change/early_review/`. A rebuild writes the same bytes.
3. `build.py` replays the decisions of all three labelling passes, applies recorded corrections, updates the database, and writes the CSV and JSON exports.
4. `public_dataset.py` writes `product_change/public/aws-announcements-2026-11-27.parquet`: every record with nine fields and no saved announcement text. It selects fields from the database and classifies nothing.
5. `charts.py` writes four SVG charts and their aggregate CSV files.
6. `verify.py` runs the integrated check.

The integrated check covers source matches, unchanged 2021–2026 decisions, the replay of every 2010–2020 decision, exports, aggregates, and drill-down counts. It also checks that the public dataset contains all 22,588 records, agrees with the database, and contains no announcement text. Its expected final message is:

```text
Verified source coverage, unchanged recent ratings, chart cells, service tags and all 22,588 CSV/JSON records.
```

In this message, source coverage means coverage of the saved corpus. The check does not prove that the corpus contains every AWS publication.

## Check the 2010–2020 evidence

These commands read the saved evidence and change no file. None of them needs network access or an AI model.

```sh
.venv/bin/python product_change/early_collect.py check     # the saved directory responses parse to 8,421 records
.venv/bin/python product_change/early_coverage.py report   # coverage against archived yearly index pages
.venv/bin/python product_change/early_samples.py check     # the hidden and bridge samples match their recorded hashes
.venv/bin/python product_change/early_label.py check 2015  # one target replays from its saved readings
.venv/bin/python product_change/early_checks.py            # 26 checks with canned replies
```

`early_label.py check` takes a year from 2010 to 2020, `bridge`, or `reference`.

## Steps that ran once

Some commands created the evidence. Running them again would replace saved inputs, draw new samples, or ask a model again, and that would destroy the independence of the audits. Do not run these commands for reproduction:

- `historical_audit.py prepare` and `historical_audit.py freeze`
- `early_collect.py collect` and `early_coverage.py fetch`
- `early_samples.py draw` and `early_human.py draw`
- `early_label.py label` on a target that is already labelled

Do not run superseded scripts under `magnitude/` to rebuild the current measure.

The 2025–2026 fresh-sample audit uses its own frozen predictions. Its saved hashes refer to that earlier snapshot, not the combined export.

## Check the recorded reproduction

`release/reproduction.json` records a successful clean-copy rebuild. It lists one SHA-256 hash for each reproduced output. A hash is a fingerprint of one file's bytes. Paths in that report are relative to `product_change/`.

To compare the rebuilt files with the recorded hashes, run:

```sh
.venv/bin/python - <<'PY'
import hashlib
import json
from pathlib import Path
report = json.loads(Path('release/reproduction.json').read_text())
for name, expected in report['reproduced_files_sha256'].items():
    path = Path('product_change') / name
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, f'Changed output: {name}'
print(f"All {len(report['reproduced_files_sha256'])} recorded output hashes match.")
PY
```

The database file can change its internal layout during rebuilding. Compare exported records and chart data rather than requiring an identical database-file hash.

## Package and share the release

From the extracted folder, run:

```sh
.venv/bin/python product_change/package.py
```

The command writes `aws_trend_explorer.zip` in the parent folder and checks the archive contents. Use a dedicated parent folder because an existing archive with that name is replaced.

Share the complete archive for local exploration and reproducible analysis. Recipients extract it and follow `README.txt`. The localhost URL works only on the computer running the server.

For a smaller analysis handoff, share the current CSV or JSON, relevant SVG charts, release notes, and audit reports together. Keep source URLs, classification reasons, and the collection cutoff with any derivative tables. This documentation does not assign a new licence to AWS source text.

The included server is a local viewer. The release bundle contains the explorer page but not the scripts that publish it as the hosted explorer. The public dataset is the only file in the release bundle prepared for publication, because it omits saved announcement text. Do not publish the rest of the release bundle.

## Report a correction

Record the source URL, current label, proposed label, supporting source text, and reason for the change. Preserve the original prediction and audit reference when recording a correction. Add it to `product_change/audit_corrections.json`, then rerun the build, the public dataset, the charts, and the verification.

Update the release date, audit evidence, and reproduction hashes for a new release. A successful rebuild establishes reproducibility, not classification accuracy. Before wider distribution, ask a new reader to follow the setup instructions; that usability check remains outstanding.
