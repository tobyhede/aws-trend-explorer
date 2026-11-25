"""Build a scoped copy of the audited DuckDB. One row and one scope per announcement URL."""
import argparse
import csv
import json
import re
import shutil
from pathlib import Path
import duckdb
from backlog.review import decisions as backlog_decisions

HERE = Path(__file__).resolve().parent
LABELS = {
    'new_product':'New product', 'new_capability':'New capability',
    'improved':'Existing capability improved', 'extended':'Existing capability extended',
    'operational':'Commercial, lifecycle or maintenance', 'unclear':'Unclear'
}
def classify(kind, facets, title, body):
    fixed = {
        'new_product':'new_product', 'commercial_change':'operational',
        'retirement_lifecycle':'operational', 'availability_expansion':'extended',
        'unknown':'unclear', 'non_product':'unclear',
    }
    if kind in fixed:
        return fixed[kind], 'Inherited release type: '+kind
    t = title.lower()
    f = set((facets or '').split('|'))
    if re.search(r'\b(patch(es)?|security fixes|bug fixes|end of support)\b',t):
        return 'operational','Maintenance or lifecycle wording in title'
    if kind=='software_release':
        return 'unclear','Version announcement; scope requires source review'
    if re.search(r'\b(ipv6|dual.stack|additional regions?|more regions?)\b',t):
        return 'extended','Protocol or geographic reach in title'
    if 'service_limit' in f or 'performance' in f:
        return 'improved','Previously assigned performance or service-limit label'
    if re.search(r'\b(expands?|extends?) (support|availability|coverage|.+? to )|\bsupport for (additional|more|newer)\b',t):
        return 'extended','Title explicitly broadens existing coverage'
    if f & {'compute_hardware_option','ai_model_catalog','software_version','geographic_availability'}:
        return 'extended','Additional hardware, model, version or geography'
    if re.search(r'\b(improves?|improved|enhances?|enhanced|simplifies|faster|simpler|upgrades?)\b',t):
        return 'improved','Title describes improving an existing operation'
    if re.search(r'\b(introduc\w+|launch(es)?|adds?|now (allows?|enables?)|integrates? with|new integration)\b',t):
        return 'new_capability','Title announces an addition or newly enabled action'
    if 'functional_capability' in f or re.search(r'\b(now|can now|customers can) (automate|create|monitor|deploy|configure|export|import|visualize|view|manage|query|detect|receive|track)\b',body[:750].lower()):
        return 'new_capability','Capability facet or explicit customer action in opening text'
    return 'unclear','Insufficient evidence of the previous customer workflow'

def stage(title):
    t=title.lower()
    for label,pattern in [('ga',r'\bgeneral(ly)? availab(le|ility)\b|\(ga\)'),('preview',r'\bpreview\b'),('lab',r'\blab mode\b')]:
        if re.search(pattern,t):
            return label
    return 'unspecified'

def build(source,dest):
    if source.resolve()==dest.resolve(): raise ValueError('Use a separate output database')
    temp=dest.with_suffix('.building.duckdb')
    shutil.copyfile(source,temp)
    sample = json.loads((HERE/'blind.json').read_text())
    readings = json.loads((HERE/'adjudicated.json').read_text())
    reviewed = {r['url']:readings[r['id']] for r in sample}
    holdout = json.loads((HERE/'v2/sample.json').read_text())
    reference = json.loads((HERE/'v2/adjudicated.json').read_text())
    for r in holdout:
        assert r['url'] not in reviewed
        reviewed[r['url']] = reference[r['id']]
    backlog=backlog_decisions()
    assert not set(reviewed).intersection(backlog)
    with duckdb.connect(str(temp)) as db:
        db.execute('drop table if exists scope_decisions')
        for name in ['primary_scope','scope_basis','title_stage']:
            db.execute(f'alter table announcements drop column if exists {name}')
        rows=db.execute("""select source_url,release_type,enhancement_facets,title,announcement_text
            from announcements where announcement_date between date '2025-01-01' and date '2026-10-28' order by source_url""").fetchall()
        decisions=[]
        for url,kind,facets,title,body in rows:
            label,basis=classify(kind,facets,title,body)
            prediction=label
            if url in reviewed:
                label=reviewed[url]['label']
                basis='Source reviewed: '+reviewed[url]['reason']
            elif url in backlog:
                label,basis=backlog[url]
            elif kind=='enhancement':
                label,basis='unclear','Enhancement awaiting source review'
            decisions.append((url,label,basis,stage(title),prediction))
        db.execute('create table scope_decisions(source_url varchar primary key, primary_scope varchar, scope_basis varchar, title_stage varchar, proposed_scope varchar)')
        db.executemany('insert into scope_decisions values (?,?,?,?,?)',decisions)
        for name in ['primary_scope','scope_basis','title_stage']:
            db.execute(f'alter table announcements add column {name} varchar')
        db.execute("""update announcements as a set primary_scope=s.primary_scope,scope_basis=s.scope_basis,title_stage=s.title_stage
            from scope_decisions s where s.source_url=a.source_url""")
        assert db.execute('select count(primary_scope) from announcements').fetchone()[0]==len(rows)
    temp.replace(dest)
    with (HERE/'decisions.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['source_url','primary_scope','scope_basis','title_stage','proposed_scope']);w.writerows(decisions)
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    build(args.source,args.output)
