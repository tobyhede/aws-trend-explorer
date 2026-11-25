import hashlib
import json
from pathlib import Path
import duckdb

here = Path(__file__).resolve().parent
def generate():
    old = {r['url'] for r in json.loads((here.parent/'blind.json').read_text())}
    with duckdb.connect(str(here.parents[1]/'announcements.duckdb'), read_only=True) as db:
        rows = db.sql("""select year(announcement_date),source_url,title,announcement_text from announcements
            where release_type='enhancement' and primary_scope is not null and strftime(announcement_date,'%m-%d')<='10-28'""").fetchall()
    sample = []
    for year in [2025,2026]:
        group = [dict(id=hashlib.sha256(('scope-v2-holdout:'+url).encode()).hexdigest()[:16],url=url,title=title,body=body)
                 for y,url,title,body in rows if y==year and url not in old]
        sample.extend(sorted(group,key=lambda r:r['id'])[:32])
    (here/'sample.json').write_text(json.dumps(sample,indent=2))
if __name__ == '__main__': generate()
