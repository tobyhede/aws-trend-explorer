"""Read-only, localhost AWS announcement explorer."""
import argparse
import csv
import io
import json
from datetime import date, timedelta
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import duckdb

HERE = Path(__file__).resolve().parent
SITE=HERE/'hosted'/'site'
MIME={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json','.svg':'image/svg+xml','.parquet':'application/vnd.apache.parquet','.txt':'text/plain; charset=utf-8','.md':'text/plain; charset=utf-8'}
def site_file(name):
    """A file of the explorer page under hosted/site, or None. Never a path outside that folder."""
    target=(SITE/name).resolve()
    return target if name and target.is_file() and SITE.resolve() in target.parents else None
DEFAULT = HERE / 'announcements.duckdb'
FIRST = date(2021, 1, 1)
LAST = date(2026, 10, 28)
FIELDS = 'announcement_date,title,service,release_type,enhancement_facets,primary_scope,scope_basis,title_stage,product_change_level,product_change_reason,product_change_basis,source_url,announcement_text'

def records(db, sql, args=()):
    cursor = db.execute(sql, args)
    fields = [x[0] for x in cursor.description]
    return [dict(zip(fields, r)) for r in cursor.fetchall()]

def filters(q):
    where, args = ['announcement_date between ? and ?'], [FIRST,LAST]
    for field, param, sep in [('primary_scope','scope',None),('release_type','type',None),('service','service','; '),('enhancement_facets','facet','|')]:
        if q.get(param):
            where.append(f"list_contains(string_split({field}, '{sep}'), ?)" if sep else f'{field} = ?')
            args.append(q[param])
    if q.get('q'):
        where.append("contains(lower(title || ' ' || announcement_text), lower(?))")
        args.append(q['q'])
    return ' AND '.join(where), args

def drill(q):
    start = date.fromisoformat(q.get('from', FIRST.isoformat()))
    end = date.fromisoformat(q.get('to', LAST.isoformat()))
    if start > end: raise ValueError('End date precedes start date.')
    where=' AND announcement_date BETWEEN ? AND ?'
    args=[start,end]
    if q.get('magnitude'):
        where+=' AND product_change_level = ?'
        args.append(q['magnitude'])
    if q.get('magnitude_matched')=='1':
        where+=" AND year(announcement_date) IN (2025,2026) AND strftime(announcement_date,'%m-%d') <= '10-28' AND product_change_level IS NOT NULL AND product_change_level != 'NA'"
    return where,args

def options(db):
    result = {}
    for key,expr in [('scope','primary_scope'),('type','release_type'),('service',"unnest(string_split(service,'; '))"),('facet',"unnest(string_split(enhancement_facets,'|'))")]:
        result[key] = [x[0] for x in db.execute(f'SELECT DISTINCT {expr} AS value FROM announcements ORDER BY value').fetchall() if x[0]]
    return result

def overview(db,q):
    where,args=filters(q)
    db.execute('CREATE TEMP TABLE selected AS SELECT announcement_date,release_type,service,enhancement_facets,primary_scope,product_change_level FROM announcements WHERE '+where,args)
    days=dict(db.execute('SELECT announcement_date,count(*) FROM selected GROUP BY 1').fetchall())
    annual=[]; months=[]; rolling=[]
    first = date(2025,1,1) if q.get("scope") else FIRST
    for year in range(first.year,LAST.year+1):
        matched=sum(n for d,n in days.items() if d.year==year and (d.month,d.day)<=(10,28))
        total=sum(n for d,n in days.items() if d.year==year)
        annual.append({'year':year,'matched':matched,'total':total})
        for month in range(1,(10 if year==LAST.year else 12)+1):
            months.append({'date':date(year,month,1),'count':sum(n for d,n in days.items() if d.year==year and d.month==month)})
    cur=first
    window=0
    while cur<=LAST:
        window+=days.get(cur,0)-days.get(cur-timedelta(days=91),0)
        if cur>=first+timedelta(days=90): rolling.append({'date':cur,'count':round(window/13,3)})
        cur+=timedelta(days=1)
    breakdown={}
    for key,expr in [('type','release_type'),('facet',"unnest(string_split(enhancement_facets,'|'))"),('service',"unnest(string_split(service,'; '))")]:
        breakdown[key]=records(db,f"""WITH tags AS (SELECT year(announcement_date) AS y,{expr} AS tag FROM selected
           WHERE year(announcement_date) IN (2025,2026) AND strftime(announcement_date,'%m-%d')<='10-28')
           SELECT tag,count(*) FILTER(WHERE y=2025) AS previous,count(*) FILTER(WHERE y=2026) AS current FROM tags
           WHERE tag IS NOT NULL GROUP BY tag ORDER BY current+previous DESC,tag""")
    scope_months=records(db,"""SELECT date_trunc('month',announcement_date)::date AS date, primary_scope AS scope,count(*) AS count
        FROM selected WHERE primary_scope IS NOT NULL GROUP BY 1,2 ORDER BY 1,2""")
    scope_delta=records(db,"""SELECT primary_scope AS scope,count(*) FILTER(WHERE year(announcement_date)=2025) AS previous,
        count(*) FILTER(WHERE year(announcement_date)=2026) AS current FROM selected
        WHERE primary_scope IS NOT NULL AND strftime(announcement_date,'%m-%d')<='10-28' GROUP BY 1 ORDER BY 1""")
    magnitude=records(db,"""SELECT primary_scope AS scope,product_change_level AS rating,year(announcement_date) AS year,count(*) AS n
        FROM selected WHERE year(announcement_date) IN (2025,2026) AND product_change_level IS NOT NULL AND product_change_level != 'NA' AND strftime(announcement_date,'%m-%d')<='10-28'
        GROUP BY 1,2,3 ORDER BY 1,2,3""")
    product_monthly=records(db,"SELECT strftime(announcement_date,'%Y-%m') AS month,product_change_level AS level,count(*) AS n FROM selected WHERE product_change_level IS NOT NULL GROUP BY 1,2 ORDER BY 1,2")
    product_annual=records(db,"SELECT year(announcement_date) AS year,product_change_level AS level,count(*) AS n FROM selected WHERE product_change_level IS NOT NULL AND strftime(announcement_date,'%m-%d')<='10-28' GROUP BY 1,2 ORDER BY 1,2")
    return {'product_monthly':product_monthly,'product_annual':product_annual,'magnitude_excluded':records(db,"SELECT year(announcement_date) AS year,count(*) AS n FROM selected WHERE year(announcement_date) IN (2025,2026) AND product_change_level='NA' AND strftime(announcement_date,'%m-%d')<='10-28' GROUP BY 1 ORDER BY 1"),'magnitude':magnitude,'scope_months':scope_months,'scope_delta':scope_delta,'annual':annual,'monthly':months,'rolling':rolling,'breakdown':breakdown,
            'total':sum(days.values()),'untagged':records(db,"SELECT year(announcement_date) AS year,count(*) AS n,count(*) FILTER(WHERE service='unknown') AS missing FROM selected WHERE strftime(announcement_date,'%m-%d')<='10-28' GROUP BY 1 ORDER BY 1")}

def serve(database, port):
    if not database.is_file(): raise SystemExit(f'Database missing: {database}')
    def connect(): return duckdb.connect(str(database),read_only=True,config={'threads':2})
    @lru_cache(maxsize=16)
    def summary(items):
        with connect() as db:return overview(db,dict(items))
    with connect() as db: choices=options(db)
    class Handler(BaseHTTPRequestHandler):
        def reply(self,body,kind,status=200):
            if isinstance(body,str):body=body.encode()
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
            if kind.startswith('text/csv'):
                name={'/architecture-rows.csv':'architecture-audit-rows.csv','/architecture-strata.csv':'architecture-strata.csv'}.get(urlsplit(self.path).path,'aws-announcements.csv')
                self.send_header('Content-Disposition',f'attachment; filename="{name}"')
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            path=urlsplit(self.path); q={k:v[-1] for k,v in parse_qs(path.query).items()}
            try:
                # The explorer is the page that is published (hosted/site). data-local tells it that saved announcement text is available here.
                if path.path=='/':return self.reply((SITE/'index.html').read_text().replace('<html lang="en">','<html lang="en" data-local>',1),'text/html; charset=utf-8')
                pages={'/product_trends.js':('product_trends.js','application/javascript'),
                       '/historical-product-audit':('product_change/historical_review/report.html','text/html'),
                       '/historical-audit.csv':('product_change/historical_review/row_audit.csv','text/csv'),
                       '/historical-audit-metrics.json':('product_change/historical_review/metrics.json','application/json'),
                       '/product-service-counts.csv':('product_change/service_matched.csv','text/csv'),
                       '/product-monthly-counts.csv':('product_change/monthly.csv','text/csv'),
                       '/product-annual-counts.csv':('product_change/matched.csv','text/csv'),
                       '/product-monthly.svg':('product_change/monthly.svg','image/svg+xml'),
                       '/product-annual.svg':('product_change/annual.svg','image/svg+xml'),
                       '/product-change-review':('product_change/review.html','text/html'),
                       '/product-change-chart.svg':('product_change/matched.svg','image/svg+xml'),
                       '/product-change-data.csv':('product_change/announcements.csv','text/csv'),
                       '/product-change-data.json':('product_change/announcements.json','application/json'),
                       '/product-change-method':('product_change/method.html','text/html'),'/architecture.js':('architecture.js','application/javascript'),
                       '/architecture.json':('magnitude/yoy_audit/architecture.json','application/json'),
                       '/architecture-audit':('magnitude/yoy_audit/audit.html','text/html'),
                       '/architecture-rows.csv':('magnitude/yoy_audit/audit_rows.csv','text/csv'),
                       '/architecture-strata.csv':('magnitude/yoy_audit/strata.csv','text/csv'),
                       '/architecture.svg':('magnitude/yoy_audit/architecture.svg','image/svg+xml'),
                       '/magnitude.js':('magnitude.js','application/javascript'),'/magnitude/audit.html':('magnitude/audit.html','text/html'),'/backlog/audit.html':('scope/backlog/audit.html','text/html'),'/scope-audit':('scope/audit.html','text/html'),'/scope.js':('scope.js','application/javascript'),'/v2/audit.html':('scope/v2/audit.html','text/html')}
                if path.path in pages:
                    filename,mime=pages[path.path]
                    if path.path in {'/architecture-audit','/architecture.json','/architecture.svg','/architecture-rows.csv','/architecture-strata.csv','/magnitude/audit.html'}:
                        return self.reply((HERE/'product_change/retired.html').read_bytes(),'text/html; charset=utf-8',410)
                    return self.reply((HERE/filename).read_bytes(),mime+'; charset=utf-8')
                static=site_file(path.path.lstrip('/'))
                if static:return self.reply(static.read_bytes(),MIME.get(static.suffix,'application/octet-stream'))
                if path.path=='/api/options': result=choices
                elif path.path=='/api/text':
                    with connect() as db:row=db.execute('SELECT announcement_text FROM announcements WHERE source_url=?',[q.get('url','')]).fetchone()
                    result={'text':row[0] if row else None}
                elif path.path=='/api/summary':result=summary(tuple(sorted((k,v) for k,v in q.items() if k in ['q','type','service','facet','scope'])))
                elif path.path in ['/api/rows','/export.csv']:
                    where,args=filters(q);w,a=drill(q);where+=w;args+=a
                    with connect() as db:
                        sql=f'SELECT {FIELDS} FROM announcements WHERE {where} ORDER BY announcement_date DESC,title,source_url'
                        if path.path=='/export.csv':
                            cur=db.execute(sql,args);buf=io.StringIO();writer=csv.writer(buf);writer.writerow([d[0] for d in cur.description]);writer.writerows(cur.fetchall())
                            return self.reply(buf.getvalue(),'text/csv; charset=utf-8')
                        offset=max(0,int(q.get('offset',0)))
                        result={'total':db.execute('SELECT count(*) FROM announcements WHERE '+where,args).fetchone()[0],
                                'rows':records(db,sql+' LIMIT 25 OFFSET ?',args+[offset])}
                else:return self.reply('Not found','text/plain',404)
                self.reply(json.dumps(result,default=str),'application/json')
            except (ValueError,duckdb.Error) as e:self.reply(str(e),'text/plain',400)
            except (BrokenPipeError,ConnectionResetError):pass
    with ThreadingHTTPServer(('127.0.0.1',port),Handler) as srv:
        print(f'http://127.0.0.1:{srv.server_port}',flush=True);srv.serve_forever()

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--database',type=Path,default=DEFAULT);ap.add_argument('--port',type=int,default=8765)
    args=ap.parse_args();serve(args.database,args.port)
