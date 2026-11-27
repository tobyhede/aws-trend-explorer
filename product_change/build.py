"""Product-change magnitude, v1. Reuses prior product scope labels; never reads consequence ratings."""
import csv
import json
from review import load_review
from pathlib import Path
import duckdb

HERE = Path(__file__).resolve().parent
NAMES = {'1':'Parameter change','2':'Capability refinement','3':'New capability',
         '4':'Major product expansion','5':'New product','U':'Needs review','NA':'Outside product-change scale'}
BASE = 'https://aws.amazon.com/about-aws/whats-new/'
REVIEWED = {
 '2025/10/aws-lambda-payload-size-256-kb-1-mb-invocations/':('1','Raises the asynchronous invocation payload ceiling from 256 KB to 1 MB.'),
 '2026/10/aws-lambda-web-functions/':('4','Introduces an HTTP-server programming and execution model, concurrent requests and active-CPU billing within Lambda.'),
 '2025/11/aws-lambda-managed-instances/':('4','Introduces a Lambda execution mode on customer EC2 instances with managed lifecycle and concurrent request handling.'),
 '2025/12/lambda-durable-multi-step-applications-ai-workflows/':('4','Extends the Lambda programming model with persistent steps, waits, checkpointing and long-running execution.'),
 '2025/07/amazon-documentdb-serverless/':('4','Adds an automatically scaling, usage-priced operating mode to DocumentDB.'),
 '2025/11/mwaa-serverless-deployment-apache-airflow-workflows/':('4','Adds a serverless execution mode with per-workflow isolation and automatic resource provisioning.'),
 '2025/07/amazon-s3-vectors-preview-native-support-storing-querying-vectors/':('4','Adds native vector storage, indexes and similarity-query APIs to S3.'),
 '2026/10/transfer-family-custom-ports-sftp/':('2','Adds port and communication-mode controls to an existing SFTP server.'),
 '2026/10/aws-lambda-durable-gen-limit-increase/':('1','Raises operation and checkpoint payload limits within existing durable execution.'),
 '2026/10/lambda-durable-telemetry/':('3','Adds a telemetry exporter and query integration for existing durable executions.'),
}
REVIEWED.update(json.loads((HERE/'audit_corrections.json').read_text()))

def classify(row, source_decisions):
    """Replay a source decision; missing coverage is an error, never a fallback."""
    return source_decisions[row[0]]

def build():
    dbpath=HERE.parent/'announcements.duckdb'
    with duckdb.connect(str(dbpath)) as db:
        rows=db.sql("""select source_url,release_type,primary_scope,enhancement_facets,title,announcement_text
            from announcements where primary_scope is not null order by source_url""").fetchall()
        recent_urls={r[0] for r in rows}
        recent_reviewed={BASE+k:v for k,v in REVIEWED.items() if BASE+k in recent_urls}
        source_decisions=load_review(rows, recent_reviewed)
        decisions=[(r[0],*classify(r,source_decisions)) for r in rows]
        from historical import load_historical, verify_recent_baseline
        verify_recent_baseline(decisions)
        historical = load_historical(db)
        decisions.extend((url, *rating) for url, rating in historical.items())
        from early_collect import COLUMNS, COHORT, parse
        from early_label import load_early
        from early_label import apply_corrections
        early = load_early()  # replays saved readings; never calls a model
        early_reviewed = {k: v for k, v in REVIEWED.items() if BASE + k in early}
        assert len(recent_reviewed) + len(early_reviewed) == len(REVIEWED), 'a correction names a record outside the reviewed cohorts'
        early = apply_corrections(early, early_reviewed)
        decisions.extend((url, *rating) for url, rating in early.items())
        assert len(decisions) == 22588 and len({r[0] for r in decisions}) == 22588
        db.begin()
        # The 2010–2020 records join the corpus from the frozen directory snapshot, replaced whole on each build.
        db.execute('delete from announcements where classification_cohort = ?', [COHORT])
        early_rows = parse()
        assert {r['source_url'] for r in early_rows} == set(early)
        db.executemany(f'insert into announcements ({",".join(COLUMNS)}) values ({",".join("?" * len(COLUMNS))})',
                       [[r[c] for c in COLUMNS] for r in early_rows])
        db.execute('create or replace table product_change_decisions(source_url varchar primary key,product_change_level varchar,product_change_reason varchar,product_change_basis varchar)')
        db.executemany('insert into product_change_decisions values (?,?,?,?)',decisions)
        for col in ['product_change_level','product_change_reason','product_change_basis']:
            db.execute(f'alter table announcements add column if not exists {col} varchar')
        db.execute("""update announcements a set product_change_level=d.product_change_level,product_change_reason=d.product_change_reason,
            product_change_basis=d.product_change_basis from product_change_decisions d where a.source_url=d.source_url""")
        db.commit()
        for ext,opts in [('csv','HEADER'),('json','ARRAY true')]:
            db.execute(f"""COPY (select announcement_date,title,service,release_type,primary_scope,enhancement_facets,
                product_change_level,product_change_reason,product_change_basis,title_stage,source_url,announcement_text
                from announcements where product_change_level is not null order by announcement_date,source_url)
                TO ? (FORMAT {ext}, {opts})""",[str(HERE/('announcements.'+ext))])
        counts=db.sql("""select year(announcement_date),product_change_level,count(*) from announcements
            where product_change_level is not null and strftime(announcement_date,'%m-%d')<='10-28'
            group by 1,2 order by 1,2""").fetchall()
    with (HERE/'matched.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['year','level','announcements']);w.writerows(counts)
    print(counts)
if __name__=='__main__':build()
