# 3. One explorer page

Date: 2026-11-26

## Status

Accepted. Replaces the earlier rule that the local and hosted explorers share no code.

## Context

The local explorer (`index.html` with `serve.py`) and the hosted explorer (`hosted/site/`) were built as separate pages. A change made and reviewed on one did not appear on the other, so the published site did not match what the maintainer had approved locally.

## Decision

There is one explorer page, `hosted/site/`. `hosted/publish.sh` uploads it as the hosted explorer. `serve.py` serves the same files as the local explorer and adds `data-local` to the page.

The page counts from the public dataset in both cases (ADR 0002). Saved announcement text stays out of the page's files (ADR 0001): when the page carries `data-local`, it reads one record's text at a time from `serve.py` (`/api/text`). The published files never carry `data-local`, and the published site has no such route.

The release bundle includes `hosted/site/` so that `serve.py` works from it.

## Consequences

- A design change is made once and is the same locally and when published.
- The local explorer no longer has full-text search or the earlier scope label views. Scope labels and saved text remain in the database and the CSV and JSON exports.
- The local explorer's search covers titles and reasons, as the hosted explorer's does.
- The earlier local page (`index.html`, `scope.js`, `magnitude.js`, `product_trends.js`) is unserved and can be removed once the maintainer confirms.
- `README.txt` and the other recipient documents still describe the earlier local page and need updating at the next release.
