"""Apply frozen source readings, validate the independent sample and export chart data."""
import csv
import json
from collections import Counter
from html import escape
from pathlib import Path
import duckdb
from validation import holdout

P=Path(__file__).resolve().parent
NAMES={'1':'Local adjustment','2':'Workflow change','3':'Architecture change','U':'Unrated'}
def load(name):
    return json.loads((P/name).read_text())
def bulk():
    result={}
    for i in range(3):
        sources=load(f'batch{i}.json')
        with (P/f'ratings{i}.tsv').open() as f:
            records=[line.rstrip('\r\n').split('\t') for line in f]
        assert len(records)==len(sources)
        for j,((idx,rating,workload,reason),source) in enumerate(zip(records,sources)):
            assert int(idx)==j and rating in NAMES and workload.strip() and reason.strip()
            assert source['url'] not in result
            result[source['url']]=dict(rating=rating,workload=workload,reason=reason,method='Batch reading')
    return result

def build():
    assigned=bulk()
    a,b=load('reader_a.json'),load('reader_b.json')
    assert set(a)==set(b)=={r['url'] for r in load('pilot.json')}
    assert all(a[u]['rating']==b[u]['rating'] for u in a)
    for url,r in a.items(): assigned[url]={**r,'method':'Two-reader pilot'}
    readings=(P/'independent.txt').read_text().splitlines()
    disputes=load('reconciled.json')
    checks=[]
    for row,line in zip(holdout(),readings,strict=True):
        rating,reason=line.split(' ',1)
        source=assigned[row['url']]
        previous=source['rating']
        assert source['method']=='Batch reading'
        if previous!=rating:
            final=disputes[row['url']]
            source.update(final)
        source['method']='Independent sample checked'
        checks.append(dict(url=row['url'],title=row['title'],batch=previous,independent=rating,independent_reason=reason,final=source['rating'],reason=source['reason']))
    assert set(disputes)=={r['url'] for r in checks if r['batch']!=r['independent']}
    assert all(r['rating'] in NAMES and r['workload'] and r['reason'] for r in assigned.values())
    screen=load('screen_review.json')
    assert set(screen)=={r['url'] for r in load('screened.json')}
    revised=sum(r['rating']!=assigned[u]['rating'] for u,r in screen.items())
    for url,r in screen.items():
        assert assigned[url]['method']=='Batch reading' and r['rating'] in NAMES and r['reason'] and r['workload']
        assigned[url]={**r,'method':'Targeted component review'}
    with (P/'validation.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=checks[0]);w.writeheader();w.writerows(checks)
    with duckdb.connect(str(P.parent/'announcements.duckdb')) as db:
        db.begin()
        expected={row[0] for row in db.sql("select source_url from announcements where primary_scope is not null and release_type='enhancement'").fetchall()}
        assert set(assigned)==expected
        for col in ['magnitude','affected_workload','magnitude_reason','magnitude_review']:
            db.execute(f'alter table announcements add column if not exists {col} varchar')
        db.execute('create temp table ratings(url varchar primary key,rating varchar,workload varchar,reason varchar,method varchar)')
        db.executemany('insert into ratings values (?,?,?,?,?)',[(u,r['rating'],r['workload'],r['reason'],r['method']) for u,r in assigned.items()])
        db.execute('update announcements a set magnitude=r.rating,affected_workload=r.workload,magnitude_reason=r.reason,magnitude_review=r.method from ratings r where a.source_url=r.url')
        assert db.sql('select count(magnitude) from announcements').fetchone()[0]==len(expected)
        db.commit()
        for ext,opt in [('csv','HEADER'),('json','ARRAY true')]:
            db.execute(f"COPY (select * from announcements where magnitude is not null order by announcement_date,source_url) TO ? (FORMAT {ext},{opt})",[str(P/('enhancements.'+ext))])
        matrix_sql="""select primary_scope, magnitude, year(announcement_date) as year, count(*) as announcements
            from announcements where magnitude is not null and strftime(announcement_date,'%m-%d')<='10-28'
            group by 1,2,3 order by 1,2,3"""
        db.execute(f"COPY ({matrix_sql}) TO ? (FORMAT csv, HEADER)",[str(P/'matrix.csv')])
        counts=db.sql("""select year(announcement_date) as year,magnitude,count(*) as n from announcements where magnitude is not null
             and strftime(announcement_date,'%m-%d')<='10-28' group by 1,2 order by 1,2""").fetchall()
    bins=Counter({(y,l):n for y,l,n in counts})
    with (P/'matched.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['year','rating','enhancements','share_percent'])
        for y in [2025,2026]:
            total=sum(bins[y,l] for l in NAMES)
            for l in NAMES:w.writerow([y,l,bins[y,l],round(100*bins[y,l]/total,2)])
    agreement=sum(r['batch']==r['independent'] for r in checks)
    confusion=Counter((r['batch'],r['independent']) for r in checks)
    table=''.join('<tr><th>'+escape(NAMES[x])+'</th>'+''.join(f'<td>{confusion[x,y]}</td>' for y in NAMES)+'</tr>' for x in NAMES)
    details=''.join('<tr><td><a href="'+escape(r['url'],quote=True)+'">'+escape(r['title'])+'</a></td>'+''.join('<td>'+escape(str(r[k]))+'</td>' for k in ('batch','independent','independent_reason','final','reason'))+'</tr>' for r in checks)
    (P/'audit.html').write_text(f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Enhancement magnitude audit</title><style>body{{margin:4vw;font:16px/1.5 system-ui;color:#173934}}p{{max-width:82ch}}td,th{{padding:8px;text-align:left;vertical-align:top;border-bottom:1px solid #ccc}}a{{color:#08645f}}</style>
    <h1>Enhancement magnitude audit</h1><p>Magnitude describes the largest substantiated change for an affected workload. A local adjustment (1) changes a parameter, compatibility, capacity or speed within a workflow. A workflow change (2) adds, removes or automates a step. An architecture change (3) removes a necessary component or enables a different deployment, recovery or data path. U means the source gives insufficient evidence. Customer adoption and business value are outside this measure.</p>
    <p>The database includes {len(assigned):,} announcements whose primary release type is enhancement, January 2025–October 28, 2026. The charts compare January 1–October 28 in each year. Each announcement counts once. Scope types used in the matrix describe what changed. Magnitude describes the consequence.</p>
    <h2>Independent readings</h2><p>Two agents independently read all 48 pilot bodies, sampling eight per group across service limits, performance, integration, automation, configuration and other enhancements. They agreed on 48/48. Three agents then split the full cohort into batches. They used titles and source passages, expanding the reading for architecture decisions. Batch notes can quote or condense source passages. The pilot's double readings take precedence over the batch ratings.</p>
    <p>A fresh sample of 80 non-pilot URLs was selected by seeded hash. An independent source reading agreed with batch ratings on {agreement}/80 before reconciliation. The matrix below has first-pass ratings down the side and independent readings across the top. A batch reviewer reconciled disagreements using the full AWS source. We also re-read {len(screen)} lower-rated, non-sample records that explicitly mentioned avoiding or replacing components. This changed {revised} ratings. Other possible architecture changes remain subject to single-reader uncertainty. These are comparisons between agent judgments. Small changes in category share may reflect rating differences.</p>
    <table><tr><th>Batch / independent</th>{''.join('<th>'+x+'</th>' for x in NAMES.values())}</tr>{table}</table>
    <h2>Validation announcements</h2><table><tr><th>Source</th><th>Batch</th><th>Independent</th><th>Independent rationale</th><th>Applied</th><th>Applied rationale</th></tr>{details}</table>""")
    print('Independent agreement',agreement,'of',len(checks),'Confusion',confusion)
if __name__=='__main__':build()
