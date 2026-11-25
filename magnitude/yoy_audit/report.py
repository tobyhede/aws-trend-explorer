"""Publish audit figures and row-level readings, and expose them in DuckDB."""
import csv
import json
from html import escape
from pathlib import Path
import duckdb

P=Path(__file__).resolve().parent
def report():
    result=json.loads((P/'architecture.json').read_text())
    with (P/'strata.csv').open() as f:strata=list(csv.DictReader(f))
    with (P/'audit_rows.csv').open() as f:rows=list(csv.DictReader(f))
    with duckdb.connect(str(P.parents[1]/'announcements.duckdb')) as db:
        db.begin()
        for table,name in [('architecture_audit_rows','audit_rows.csv'),('architecture_audit_strata','strata.csv')]:
            db.execute(f'create or replace table {table} as select * from read_csv(?,header=true)',[str(P/name)])
        assert db.sql('select count(distinct url) from architecture_audit_rows join announcements on url=source_url').fetchone()[0]==len(rows)
        db.commit()
    years=result['years'];d=result['difference'];n=result['sample'];agreement=result['agreement']
    v=''.join(f'<tr><th>{r["year"]}</th><td>{r["total"]:,}</td><td>{r["observed"]} ({r["observed_share"]:.1f}%)</td><td>≈{r["adjusted"]:.0f} ({r["adjusted_share"]:.1f}%)</td><td>{r["count_interval"][0]}–{r["count_interval"][1]}</td><td>{r["share_interval"][0]:.1f}–{r["share_interval"][1]:.1f}%</td></tr>' for r in years)
    groups=''.join('<tr>'+''.join('<td>'+escape(r[k])+'</td>' for k in ('year','rating','total','carried','eligible','sample','architecture'))+'</tr>' for r in strata)
    terms={True:'Architecture',False:'Other','True':'Architecture','False':'Other'}
    examples=''.join('<tr><td><a href="'+escape(r['url'],quote=True)+'">'+escape(r['title'])+'</a></td>'+''.join('<td>'+escape(v)+'</td>' for v in [r['year'],r['rating'],terms[r['reader_a']],terms[r['reader_b']],terms[r['architecture']],r['reason']])+'</tr>' for r in rows)
    fixed=sum(y['carried'] for y in years)
    sign='inconclusive' if d['share_interval'][0]<=0<=d['share_interval'][1] else ('positive' if d['share_pp']>0 else 'negative')
    conclusion=f'The estimated change in architecture share was {d["share_pp"]:+.1f} percentage points. Its 95% credible interval runs from {d["share_interval"][0]:+.1f} to {d["share_interval"][1]:+.1f} points. The direction is {sign}.'
    (P/'audit.html').write_text(f'''<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Architecture-change trend audit</title>
    <style>body{{font:16px/1.55 system-ui;color:#173934;margin:4vw}}p{{max-width:86ch}}td,th{{padding:7px;text-align:left;border-bottom:1px solid #ccd6d2;vertical-align:top}}table{{border-collapse:collapse}}a{{color:#08645f}} .wide{{overflow-x:auto}}</style>
    <h1>Did architecture changes become more common?</h1><p>{conclusion} The estimated count difference was {d['count']:+.0f} announcements, with a 95% credible interval of {d['count_interval'][0]:+} to {d['count_interval'][1]:+}.</p>
    <table><tr><th>Jan 1–Oct 28</th><th>Enhancements</th><th>As published</th><th>Audit estimate</th><th>95% count interval</th><th>95% share interval</th></tr>{v}</table>
    <p>The published counts describe the frozen row-level classifications. The audit estimates how many announcements meet the architecture criterion after accounting for missed and extra assignments. Each announcement is counted once. The evidence concerns the design available to affected customers. Customer adoption was not measured.</p>
    <h2>Sampling and estimation</h2><p>We split the matched period in each year into four original magnitude ratings. A seeded hash of each official announcement URL selected 40 single-reader rows from each local, workflow and architecture group. We sampled every single-reader unrated enhancement. This produced {n} fresh cases. The {fixed} previously reviewed pilot, validation and targeted cases were carried at their existing decisions; they supplied no evidence about unreviewed rows.</p>
    <p>Two independent agents saw the title and source text with a random identifier. Year and original labels were omitted from the assignment fields; AWS text could itself mention a date. Readers agreed on {agreement}/{n}. A third reader reconciled disagreements against the full text while blinded to the original labels. A positive judgment identifies a component made unnecessary or a materially different deployment, recovery or data path enabled by this announcement.</p>
    <p>For each year and original rating, the point estimate multiplies the eligible population by the fraction of fresh readings judged architectural. These estimates are added to previously reviewed architecture counts. The 95% model-based ranges use 60,000 seeded draws. For each stratum a Jeffreys Beta(½, ½) prior on the architecture fraction is updated with the sample, then a beta-binomial draw supplies the number of architecture cases among only the unsampled records. We retain observed sample outcomes, and fully examined strata have no sampling uncertainty. Differences are calculated within each paired draw. The ranges are conditional on the source inventory, earlier review decisions and reconciled judgments.</p>
    <p>As a sensitivity check, inversion of exact hypergeometric tails with a simultaneous Bonferroni correction across the six non-census strata gives a conservative 95% design-based range for the change in share of {d['exact_share_interval'][0]:+.1f} to {d['exact_share_interval'][1]:+.1f} percentage points.</p>
    <h2>Sample by year and original rating</h2><table><tr><th>Year</th><th>Rating</th><th>Total</th><th>Prior review</th><th>Eligible</th><th>Read</th><th>Read as architecture</th></tr>{groups}</table>
    <h2>Individual readings</h2><div class=wide><table><tr><th>AWS source</th><th>Year</th><th>Original rating</th><th>Reader A</th><th>Reader B</th><th>Final</th><th>Reason</th></tr>{examples}</table></div>''')
    # Portable chart with a common share scale and separate observed and estimated symbols.
    max_value=max(y['share_interval'][1] for y in years)+3
    x=lambda v:145+v/max_value*480
    marks=[]
    for i,y in enumerate(years):
        cy=113+i*76
        lo,hi=map(x,y['share_interval'])
        obs=x(y['observed_share']);center=x(y['adjusted_share'])
        marks.append(f'<text x="24" y="{cy+5}">{y["year"]}</text><path d="M{lo} {cy}H{hi} M{lo} {cy-6}v12 M{hi} {cy-6}v12" fill="none" stroke="#086c67" stroke-width="2"/><circle cx="{center}" cy="{cy}" r="5" fill="#086c67"/><path d="M{obs} {cy-21}l5 5-5 5-5-5z" fill="#b25637"/><text x="{center}" y="{cy+23}" text-anchor="middle">{y["adjusted_share"]:.1f}%</text>')
    (P/'architecture.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 675 268" style="font:15px sans-serif;fill:#173934"><rect width="675" height="268" fill="#f6f8f1"/><text x="24" y="34" font-size="24">Architecture changes as a share of enhancements</text><text x="24" y="61">Matched January 1–October 28 windows</text>'+''.join(marks)+'<text x="24" y="250">◆ Published share　　● Audit estimate and 95% credible interval</text></svg>')
if __name__=='__main__':report()
