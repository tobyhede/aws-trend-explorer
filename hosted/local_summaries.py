"""Print the local explorer's summaries for a fixed list of filter sets, for hosted/check.mjs to compare.

Usage: python hosted/local_summaries.py '[{"type": "enhancement"}, ...]'
Reads the database read-only through serve.py's own query functions. Search filters are not accepted:
the local explorer searches saved announcement text, which the hosted explorer does not have.
"""
import json
import sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import serve


def main():
    queries = json.loads(sys.argv[1])
    assert all(set(q) <= {'type', 'service', 'facet'} for q in queries)
    results = []
    for q in queries:
        with duckdb.connect(str(serve.DEFAULT), read_only=True) as db:
            data = serve.overview(db, q)
        results.append({key: data[key] for key in ['total', 'annual', 'product_annual', 'product_monthly', 'breakdown']})
    with duckdb.connect(str(serve.DEFAULT), read_only=True) as db:
        results[0]['options'] = serve.options(db)
        where, args = serve.filters({'service': 'amazon-s3'})
        results[0]['s3_order'] = [r[0] for r in db.execute(
            f'SELECT source_url FROM announcements WHERE {where} ORDER BY announcement_date DESC,title,source_url', args).fetchall()]
    json.dump(results, sys.stdout, default=str)


if __name__ == '__main__':
    main()
