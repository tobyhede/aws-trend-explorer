"""Freeze matched-period strata. Earlier reviewed records are carried as a separate fixed partition."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import duckdb

HERE=Path(__file__).resolve().parent
SEED='architecture-yoy-audit-2026-v1'
def digest(url):
    return hashlib.sha256((SEED+'|'+url).encode()).hexdigest()
def generate():
    groups=defaultdict(list)
    blind=[]
    frame=[]
    with duckdb.connect(str(HERE.parents[1]/'announcements.duckdb'),read_only=True) as db:
        records=db.sql("""SELECT year(announcement_date),source_url,title,announcement_text,magnitude,magnitude_review
            FROM announcements WHERE magnitude IS NOT NULL AND strftime(announcement_date,'%m-%d')<='10-28'
            ORDER BY source_url""").fetchall()
    for year,url,title,body,rating,review in records:
        item=dict(id=digest(url)[:16],year=year,url=url,rating=rating,previous_review=review)
        frame.append(item)
        if review=='Batch reading':groups[year,rating].append((item,title,body))
    for rows in groups.values():
        for item,title,body in sorted(rows,key=lambda r:r[0]['id'])[:40]:
            blind.append(dict(id=item['id'],title=title,body=body))
    blind.sort(key=lambda r:r['id'])
    chosen={r['id'] for r in blind}
    assert len(chosen)==len(blind) and len({r['id'] for r in frame})==2820
    with (HERE/'frame.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=[*frame[0],'selected']);w.writeheader()
        for r in frame:w.writerow(dict(**r,selected=int(r['id'] in chosen)))
    (HERE/'blind.json').write_text(json.dumps(blind,indent=1))
    print(len(blind),'fresh cases')
if __name__=='__main__':generate()
