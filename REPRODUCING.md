# Reproduce and share the AWS explorer release

Release: 25 November 2026. The archive contains data, saved review evidence, analysis code, and charts. Reproduction replays recorded judgments; it does not ask an AI model to classify the records again.

## Run the included data

Follow `README.txt` to install the pinned dependency and start the local explorer. The tested environment uses Python 3.13.7 and DuckDB 1.5.6. If you only need static figures, open SVG charts directly in a browser.

## Rebuild the outputs

Work in a copy of the extracted archive. Stop the explorer before changing its database. Run these commands from the extracted folder after installing its requirements:

```sh
.venv/bin/python product_change/historical_audit.py score
.venv/bin/python product_change/build.py
.venv/bin/python product_change/charts.py
.venv/bin/python product_change/verify.py
```

The first command scores the frozen initial predictions against the saved references. The build applies recorded corrections, updates the database, and writes current CSV and JSON exports. The chart command writes four SVG charts and their aggregate CSV files.

The verification command checks source matches, unchanged recent decisions, exports, aggregates, and drill-down counts. Its expected final message is:

```text
Verified source coverage, unchanged recent ratings, chart cells, service tags and all 14,167 CSV/JSON records.
```

In this message, source coverage means coverage of the saved corpus. The check does not prove that the corpus contains every AWS publication.

Do not run the historical audit's `prepare` or `freeze` commands for reproduction. Those commands create review inputs or references. Do not run superseded scripts under `magnitude/` to rebuild the current measure.

The recent fresh-sample audit uses its own frozen predictions. Its saved hashes refer to that earlier snapshot, not the combined historical export.

## Check the recorded reproduction

`release/reproduction.json` records a successful clean-copy rebuild of 12 outputs. Each SHA-256 hash is a fingerprint of one file's bytes. Paths in that report are relative to `product_change/`.

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
print('All 12 recorded output hashes match.')
PY
```

The database file itself can change its internal layout during rebuilding. Compare exported records and chart data rather than requiring an identical database-file hash.

## Package and share the release

From the extracted folder, run:

```sh
.venv/bin/python product_change/package.py
```

The command writes `aws_trend_explorer.zip` in the parent folder and checks the archive contents. Use a dedicated parent folder because an existing archive with that name is replaced.

Share the complete archive for local exploration and reproducible analysis. Recipients extract it and follow `README.txt`. The localhost URL works only on the computer running the server.

For a smaller analysis handoff, share the current CSV or JSON, relevant SVG charts, release notes, and audit report together. Keep source URLs, classification reasons, and the collection cutoff with any derivative tables. This documentation does not assign a new licence to AWS source text.

The included server is a local viewer. Public hosting, authentication, and a hosted download page are not part of this release.

## Report a correction

Record the source URL, current label, proposed label, supporting source text, and reason for the change. Preserve the original prediction and audit reference when recording a correction. Rerun the build, charts, and verification after an accepted change.

Update the release date, audit evidence, and reproduction hashes for a new release. A successful rebuild establishes reproducibility, not classification accuracy. Before wider distribution, ask a new reader to follow the setup instructions; that usability check remains outstanding.
