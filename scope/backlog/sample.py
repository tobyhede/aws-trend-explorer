"""Freeze the previously unresolved URL inventory and a blinded random validation sample."""
import hashlib,json
from pathlib import Path
import duckdb
P=Path(__file__).resolve().parent
if __name__=='__main__':
 with duckdb.connect(str(P.parents[1]/'announcements.duckdb'),read_only=True) as db:
    rows=[dict(url=u,title=t,body=b) for u,t,b in db.sql("select source_url,title,announcement_text from announcements where primary_scope='unclear' order by source_url").fetchall()]
 assert len(rows)==3505,'Run against the pre-backlog snapshot'
 for i in range(3):
    (P/f'batch{i}.json').write_text(json.dumps(rows[i::3],ensure_ascii=False))
 sample=sorted(rows,key=lambda r:hashlib.sha256(('backlog-blind-validation-01'+r['url']).encode()).digest())[:100]
 (P/'validation.json').write_text(json.dumps(sample,ensure_ascii=False))
