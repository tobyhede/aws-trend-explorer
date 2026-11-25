"""Regenerate the scope audit, row-level exports and standalone scope chart."""
import csv
import json
from html import escape
from pathlib import Path
import duckdb
from build import LABELS

HERE=Path(__file__).resolve().parent
def report():
    load=lambda name: json.loads((HERE/name).read_text())
    rows=load('blind.json')
    readers=[load(n) for n in ['reader_a.json','reader_b.json','adjudicated.json']]
    with duckdb.connect(str(HERE.parent/'announcements.duckdb'),read_only=True) as db:
        sql="""select primary_scope,count(*) filter(where year(announcement_date)=2025) as prior,
            count(*) filter(where year(announcement_date)=2026) as current from announcements
            where primary_scope is not null and strftime(announcement_date,'%m-%d')<='10-28' group by 1 order by current-prior desc"""
        changes=db.execute(sql).fetchall()
        proposals=dict(db.execute('select source_url,proposed_scope from scope_decisions').fetchall())
        for ext,options in [('csv','HEADER'),('json','ARRAY true')]:
            db.execute(f"COPY (select * from announcements where primary_scope is not null order by announcement_date,source_url) TO ? (FORMAT {ext}, {options})",[str(HERE/('announcements.'+ext))])
    matches=hits=0
    detail=[]
    for r in rows:
        a,b,ref=[reader[r['id']]['label'] for reader in readers]
        proposed=proposals[r['url']]
        matches+=a==b
        hits+=proposed==ref
        title=f'<a href="{escape(r["url"],quote=True)}">{escape(r["title"])}</a>'
        detail.append('<tr><td>'+title+'</td>'+''.join('<td>'+escape(LABELS[v])+'</td>' for v in [a,b,proposed,ref])+'<td>'+escape(readers[-1][r['id']]['reason'])+'</td></tr>')
    (HERE/'audit.html').write_text(f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>AWS announcement scope audit</title>
    <style>body{{max-width:1150px;margin:3rem auto;padding:0 1rem;font:16px/1.5 system-ui;color:#173934}}p{{max-width:80ch}}table{{border-collapse:collapse;font-size:14px}}td,th{{text-align:left;padding:9px;border-bottom:1px solid #ccd6d2}}a{{color:#08645f}}</style>
    <h1>How we assigned scope</h1><p>One English AWS announcement URL counts once. Scope coverage begins January 1, 2025 and ends October 28, 2026. Annual comparisons end October 28 in both years. November and December 2025 contribute to the monthly chart and rolling averages.</p>
    <p><a href="backlog/audit.html">Open the backlog validation</a> · <a href="v2/audit.html">Open the 64-announcement before/after evaluation</a></p>
    <h2>What the audit found</h2><p>Two readers classified 48 enhancements independently from their AWS titles and bodies. The readers agreed on {matches}/48. Reader A subsequently reconciled the two readings against the source text. The proposed automated scope agreed with those decisions on {hits}/48. A second audit evaluated a before/after source-reading heuristic on 64 fresh announcements. The explorer applies reviewed decisions from both samples. A subsequent source-reading pass classified the 3,505 previously unresolved announcements. Its independent validation is linked above.</p>
    <p>The deterministic sample selected eight rows per year from each of three groups in the matched periods: integration, performance or service limit, and other. Integration took priority for overlapping labels. Raw agreement describes this sample. It does not measure population accuracy or prevalence.</p>
    <p>Existing product and regional-availability release types map to new product and extended respectively. Commercial and retirement announcements map to operational. Explicit maintenance wording can also map a software release to operational. The backlog pass examined version releases, unknowns and non-product posts individually. This sample tested enhancement scope only. Missing historical posts or errors in upstream labels can affect counts.</p>
    <p>Each row retains its enhancement labels, the reason for its scope assignment, and a stage extracted only when the title explicitly mentions preview, general availability or lab mode. Stage is unspecified otherwise. These charts count posts, including separate posts for different stages of a capability.</p>
    <h2>Source decisions</h2><table><tr><th>Announcement</th><th>Reader A</th><th>Reader B</th><th>Automated proposal</th><th>Applied scope</th><th>Reason</th></tr>{''.join(detail)}</table>""")
    with (HERE/'matched_counts.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['scope','2025','2026','change']);w.writerows((s,a,b,b-a) for s,a,b in changes)
    # Render a standalone vector chart with the same matched counts used by the explorer.
    marks=[]
    max_delta=max(abs(b-a) for _,a,b in changes)
    for i,(scope,a,b) in enumerate(changes):
        y=103+45*i; delta=b-a; width=abs(delta)/max_delta*170
        marks.append(f'<text x="20" y="{y}">{LABELS[scope]}</text><rect x="{480-width if delta<0 else 480}" y="{y-12}" width="{width}" height="15" fill="{("#85908e" if scope=="unclear" else "#086c67")}"/><text x="710" y="{y}" text-anchor="end">{delta:+}</text>')
    (HERE/'scope_change.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 745 420" style="font:15px sans-serif;fill:#183438"><rect width="100%" height="100%" fill="#f7f7f1"/><text x="20" y="34" font-size="24">Change in announcements by scope</text><text x="20" y="61">January 1–October 28, 2026 compared with the same dates in 2025</text><path d="M480 78V347" stroke="#909a99"/>'+''.join(marks)+'<text x="20" y="385">Backlog scope labels use agent readings of AWS announcements. See the validation sample.</text></svg>')

if __name__=='__main__': report()
