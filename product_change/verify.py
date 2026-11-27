"""Check the revised data through the explorer's query and drilldown entry points."""
import csv
import json
import sys
from pathlib import Path
import duckdb
from build import REVIEWED, BASE

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import serve

def verify_public_dataset(db):
    """The public dataset holds every record, the nine public fields and no saved announcement text."""
    from public_dataset import FIELDS, PATH
    assert PATH.is_file(), f'Public dataset missing: run product_change/public_dataset.py ({PATH.name})'
    assert [p.name for p in PATH.parent.glob('*.parquet')]==[PATH.name]
    file=str(PATH)
    schema={name:kind for name,kind,*_ in db.execute('describe select * from read_parquet(?)',[file]).fetchall()}
    assert list(schema)==FIELDS and len(FIELDS)==9 and 'announcement_text' not in schema
    assert schema['announcement_date']=='DATE' and all(kind=='VARCHAR' for name,kind in schema.items() if name!='announcement_date')
    assert db.execute('select count(*),count(distinct source_url) from read_parquet(?)',[file]).fetchone()==(14167,14167)
    columns=','.join(FIELDS)
    # The public dataset still describes the 25 November 2026 release (2021–2026) until stage two rebuilds it.
    released="(select * from announcements where announcement_date >= '2021-01-01')"
    for left,right in [(released,'read_parquet(?)'),('read_parquet(?)',released)]:
        assert db.execute(f'select count(*) from (select {columns} from {left} except select {columns} from {right})',[file]).fetchone()[0]==0
    text_fields=" || ' ' || ".join(f"coalesce(p.{name},'')" for name in FIELDS if name not in ['announcement_date','title'])
    leaked=db.execute(f"""select count(*) from read_parquet(?) p join announcements a using (source_url)
        where length(a.announcement_text)>length(a.title) and contains({text_fields},a.announcement_text)""",[file]).fetchone()[0]
    assert leaked==0, f'{leaked} public records contain saved announcement text'

def verify():
    from historical import load_initial, verify_recent_baseline
    with duckdb.connect(str(HERE.parent/'announcements.duckdb'),read_only=True) as db:
        data=serve.overview(db,{})
        for row in data['magnitude']:
            q={'scope':row['scope'],'magnitude':row['rating'],'magnitude_matched':'1','from':f"{row['year']}-01-01",'to':f"{row['year']}-10-28"}
            where,args=serve.filters(q);drill,extra=serve.drill(q)
            actual=db.execute('select count(*) from announcements where '+where+drill,args+extra).fetchone()[0]
            assert actual==row['n']
        for y,total in [(2025,2018),(2026,2257)]:
            assert sum(r['n'] for r in data['magnitude']+data['magnitude_excluded'] if r['year']==y)==total
        for row in data['product_annual']:
            q={'magnitude':row['level'],'from':f"{row['year']}-01-01",'to':f"{row['year']}-10-28"}
            where,args=serve.filters(q);drill,extra=serve.drill(q)
            assert db.execute('select count(*) from announcements where '+where+drill,args+extra).fetchone()[0]==row['n']
        for row in data['product_monthly']:
            assert db.execute("select count(*) from announcements where strftime(announcement_date,'%Y-%m')=? and product_change_level=?",[row['month'],row['level']]).fetchone()[0]==row['n']
        decisions=db.sql('select * from product_change_decisions').fetchall()
        expected={r[0]:r[1] for r in decisions}
        assert len(expected)==22588
        verify_recent_baseline(decisions)
        from historical import load_historical
        from early_label import load_early, apply_corrections
        decision_map={r[0]:tuple(r[1:]) for r in decisions}
        assert all(decision_map[url]==row for url,row in load_historical(db).items()), 'a 2021–2024 decision changed'
        early=load_early()
        early=apply_corrections(early,{k:v for k,v in REVIEWED.items() if BASE+k in early})
        assert len(early)==8421 and all(decision_map[url]==row for url,row in early.items()), 'a 2010–2020 decision does not replay its saved evidence and recorded corrections'
        assert db.sql("select count(*) from announcements where announcement_date < '2021-01-01'").fetchone()[0]==8421
        for column in ['primary_scope','title_stage','release_type','enhancement_facets','legacy_category','magnitude','affected_workload','magnitude_reason','magnitude_review']:
            assert db.sql(f"select count(*) from announcements where announcement_date < '2021-01-01' and {column} is not null").fetchone()[0]==0, column
        sources, initial=load_initial(db)
        assert len(sources)==9247
        assert db.sql("select count(*) from announcements where announcement_date < '2025-01-01' and primary_scope is not null").fetchone()[0]==0
        assert dict(db.sql('select year(announcement_date),count(*) from announcements group by 1').fetchall())=={2010:66,2011:82,2012:91,2013:185,2014:295,2015:452,2016:640,2017:1023,2018:1433,2019:1860,2020:2294,
            2021:2084,2022:2103,2023:2715,2024:2345,2025:2663,2026:2257}
        report=json.loads((HERE/'review_report.json').read_text())
        assert report['source_records']==4920 and report['sample_size']==120
        assert dict(db.sql("select product_change_level,count(*) from announcements where announcement_date >= '2025-01-01' group by 1").fetchall())==report['counts']
        audit=json.loads((HERE/'sample_audit.json').read_text())
        assert len(audit)==120 and len({r['source_url'] for r in audit})==120
        assert sum(r['first_level']==r['independent_level'] for r in audit)==report['independent_exact_agreement']
        assert all(expected[r['source_url']]==r['final_level'] for r in audit)
        for name in ['annual','monthly','service_matched']:
            aggregate=list(csv.DictReader((HERE/(name+'.csv')).open()))
            assert aggregate and all(int(r['announcements'])>0 for r in aggregate)
            if name in ['annual','monthly']:assert sum(int(r['announcements']) for r in aggregate)==22588
            else:
                actual={(str(y),service,level):n for y,service,level,n in db.sql("select year(announcement_date),tag,product_change_level,count(*) from announcements,unnest(string_split(service,'; ')) tags(tag) where strftime(announcement_date,'%m-%d')<='10-28' group by 1,2,3").fetchall()}
                assert {(r['year'],r['service'],r['level']):int(r['announcements']) for r in aggregate}==actual
        for name in ['matched.svg','annual.svg','annual_full.svg','monthly.svg']:
            assert '<svg' in (HERE/name).read_text()
        for path,(level,_) in REVIEWED.items():assert expected[BASE+path]==level
        for ext in ['csv','json']:
            with (HERE/('announcements.'+ext)).open() as f:
                rows=list(csv.DictReader(f)) if ext=='csv' else json.load(f)
            assert len(rows)==22588 and {r['source_url']:r['product_change_level'] for r in rows}==expected
            assert not any('magnitude' in key for key in rows[0])
            for row in rows:
                assert decision_map[row['source_url']]==(row['product_change_level'],row['product_change_reason'],row['product_change_basis'])
        verify_public_dataset(db)
    html=(HERE.parent/'index.html').read_text()
    assert 'architectureTitle' not in html and '/architecture.js' not in html
    print('Verified source coverage, unchanged recent ratings, chart cells, service tags and all 22,588 CSV/JSON records.')
if __name__=='__main__':verify()
