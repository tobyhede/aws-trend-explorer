import hashlib,json
from pathlib import Path
import duckdb
P=Path(__file__).resolve().parent
if __name__=='__main__':
    with duckdb.connect(str(P.parent/'announcements.duckdb'),read_only=True) as db:
        rows=[dict(url=u,title=t,body=b,facets=f or '') for u,t,b,f in db.sql("select source_url,title,announcement_text,enhancement_facets from announcements where primary_scope is not null and release_type='enhancement' order by source_url").fetchall()]
    for r in rows:
        r['group']=next((g for g in ['service_limit','performance','integration_compatibility','operational_automation','configuration_user_workflow'] if g in r['facets'].split('|')),'other')
    pilot=[]
    for g in sorted({r['group'] for r in rows}):
        pilot+=sorted((r for r in rows if r['group']==g),key=lambda r:hashlib.sha256(('magnitude-pilot-1'+r['url']).encode()).digest())[:8]
    for i in range(3):
        (P/f'batch{i}.json').write_text(json.dumps(rows[i::3]))
    (P/'pilot.json').write_text(json.dumps(pilot))
