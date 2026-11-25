"""Score three scope methods on the same held-out sources and regenerate the audit."""
import csv
import json
import sys
from collections import Counter
from html import escape
from pathlib import Path
import duckdb
from rules import predict

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from build import classify, LABELS

def read(name):
    return json.loads((HERE/name).read_text())
def evaluate():
    rows=read('sample.json')
    ids={r['id'] for r in rows}
    ca,ra,rb,truth=[read(name+'.json') for name in ('candidate','ref_a','ref_b','adjudicated')]
    assert all(set(x)==ids for x in (ca,ra,rb,truth))
    dbpath=HERE.parents[1]/'announcements.duckdb'
    out=[]
    with duckdb.connect(str(dbpath),read_only=True) as db:
        for r in rows:
            i=r['id']
            assert ca[i]['evidence'] and ca[i]['evidence'] in r['title']+' '+r['body']
            facets=db.execute('select enhancement_facets from announcements where source_url=?',[r['url']]).fetchone()[0]
            old,_=classify('enhancement',facets,r['title'],r['body'])
            keyword,evidence=predict(r['title'],r['body'])
            out.append(dict(id=i,url=r['url'],title=r['title'],reference=truth[i]['label'],
                reader_a=ra[i]['label'],reader_b=rb[i]['label'],baseline=old,text_rule=keyword,
                heuristic=ca[i]['label'],before=ca[i]['before'],after=ca[i]['after'],evidence=ca[i]['evidence'],
                reference_reason=truth[i]['reason'],rule_evidence=evidence))
    with (HERE/'comparison.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=out[0]);writer.writeheader();writer.writerows(out)
    scores={}
    for method in ('baseline','text_rule','heuristic'):
        counts=Counter((r['reference'],r[method]) for r in out)
        scores[method]={'matches':sum(n for (a,b),n in counts.items() if a==b),'classified':sum(n for (a,b),n in counts.items() if b!='unclear'),
            'by_label':{l:{'reference':sum(n for (a,b),n in counts.items() if a==l),'predicted':sum(n for (a,b),n in counts.items() if b==l),'matches':counts[l,l]} for l in LABELS}}
    audit={'sample':len(out),'reference_agreement':sum(r['reader_a']==r['reader_b'] for r in out),'scores':scores}
    (HERE/'metrics.json').write_text(json.dumps(audit,indent=2))
    def cell(v):return '<td>'+escape(str(v))+'</td>'
    table=''.join('<tr><td><a href="'+escape(r['url'],quote=True)+'">'+escape(r['title'])+'</a></td>'+''.join(cell(r[k]) for k in ('before','after','evidence','heuristic','reference','reference_reason'))+'</tr>' for r in out)
    method_rows=''.join('<tr>'+cell(label)+cell(scores[key]['matches'])+cell(scores[key]['classified'])+'</tr>' for key,label in [('baseline','Original rules'),('text_rule','Conservative text rules'),('heuristic','Before/after source reading')])
    (HERE/'audit.html').write_text(f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Scope heuristic evaluation</title>
    <style>body{{font:16px/1.5 system-ui;color:#173934;margin:3vw}}p,pre{{max-width:88ch}}pre{{font:inherit;white-space:pre-wrap}}td,th{{padding:8px;border-bottom:1px solid #ccc;text-align:left;vertical-align:top}}table{{border-collapse:collapse}}a{{color:#08645f}}</style>
    <h1>Scope heuristic evaluation</h1><p>64 previously unreviewed enhancements, 32 from each matched January 1–October 28 window in 2025 and 2026. URLs were sampled by seeded hash within year. Two agents independently read the AWS text and agreed on {audit['reference_agreement']} of 64. A separate reconciliation of their differences used the source text. A third agent applied the before/after heuristic blind to the references. These results measure agreement with agent judgments on this sample.</p>
    <table><tr><th>Method</th><th>Matches out of 64 (including unclear)</th><th>Non-unclear predictions</th></tr>{method_rows}</table>
    <h2>Decision guide</h2><pre>{escape((HERE/'heuristic.txt').read_text())}</pre>
    <h2>Source evidence and disagreements</h2><table><tr><th>AWS announcement</th><th>Before (candidate reading)</th><th>After</th><th>Source evidence</th><th>Candidate</th><th>Reconciled</th><th>Reference rationale</th></tr>{table}</table>""")
    print(json.dumps(audit))
if __name__=='__main__':evaluate()
