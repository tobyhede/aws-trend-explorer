# The hosted explorer counts in plain JavaScript, not DuckDB-Wasm

The local explorer and the build both use DuckDB, so DuckDB-Wasm was the obvious choice for the hosted explorer. We rejected it: the engine file is about 36 MB, and the public dataset is about 1.5 MB and 14,167 records, which plain JavaScript filters and counts in milliseconds. The hosted explorer reads one dated Parquet file with a small reader library checked into the repository, and that same file is the download for anyone who wants to run SQL in their own DuckDB.

## Consequences

- The counting logic exists twice: SQL in `serve.py` and JavaScript in the hosted explorer. A check must compare the JavaScript counts with `matched.csv` and `monthly.csv`, and it needs Node as a development-only requirement.
- Visitors cannot write SQL on the page.
- Revisit this if the public dataset grows well beyond what a browser can hold in memory, or if a view needs joins or window functions.
