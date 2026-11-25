"""Build a deterministic blind sample, stratified by year and evidence of boundary cases."""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
import duckdb

HERE = Path(__file__).resolve().parent
def sample(database):
    with duckdb.connect(str(database), read_only=True) as db:
        rows = db.execute("""select year(announcement_date),source_url,title,announcement_text,enhancement_facets
            from announcements where release_type='enhancement' and year(announcement_date) in (2025,2026)
            and strftime(announcement_date,'%m-%d') <= '10-28'""").fetchall()
    groups = defaultdict(list)
    for year,url,title,body,facets in rows:
        f = (facets or '').lower()
        group = 'integration' if 'integration' in f else 'performance-limit' if 'performance' in f or 'limit' in f else 'other'
        groups[year,group].append(dict(id=hashlib.sha256(('scope-audit-1'+url).encode()).hexdigest()[:16],url=url,title=title,body=body))
    chosen = []
    with (HERE/'strata.csv').open('w') as out:
        writer=csv.writer(out)
        writer.writerow(['year','stratum','population','sample'])
        for (year,group),items in sorted(groups.items()):
            subset=sorted(items,key=lambda r:r['id'])[:8]
            chosen.extend(subset)
            writer.writerow([year,group,len(items),len(subset)])
    (HERE/'blind.json').write_text(json.dumps(sorted(chosen,key=lambda r:r['id']),indent=2))
if __name__=='__main__':
    sample(sys.argv[1])
