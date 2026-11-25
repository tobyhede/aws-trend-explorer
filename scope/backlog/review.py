"""Join frozen first readings and independent validation by official announcement URL."""
import csv
import json
from collections import Counter
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = dict(N='new_capability', I='improved', E='extended', P='new_product', O='operational', U='unclear')

def load_labels(data, labels):
    rows=json.loads((HERE/data).read_text())
    codes=''.join((HERE/labels).read_text().split())
    assert len(rows)==len(codes) and set(codes)<=LABELS.keys()
    return [(r,LABELS[c]) for r,c in zip(rows,codes)]

def first_readings():
    predictions={}
    for batch in range(3):
        for r,label in load_labels(f'batch{batch}.json',f'labels{batch}.txt'):
            assert r['url'] not in predictions
            predictions[r['url']]=label
    assert len(predictions)==3505
    return predictions

def comparisons():
    predictions=first_readings()
    return [(r,predictions[r['url']],ref) for r,ref in load_labels('validation.json','validation_labels.txt')]

def decisions():
    results={url:(label,'Backlog first reading of AWS announcement') for url,label in first_readings().items()}
    rare=json.loads((HERE/'rare_review.json').read_text())
    for url,rec in rare.items():
        assert url in results and rec['label'] in LABELS.values()
        results[url]=(rec['label'],'Targeted scope review: '+rec['reason'])
    final=json.loads((HERE/'reconciled.json').read_text())
    assert set(final)=={r['url'] for r,pred,ref in comparisons() if pred!=ref}
    for r,pred,ref in comparisons():
        if pred==ref:
            label,reason=ref,'Independent readings agree'
        else:
            rec=final[r['url']]
            label,reason=rec['label'],rec['reason']
            assert label in LABELS.values()
        results[r['url']]=(label,'Backlog validation: '+reason)
    return results

def report():
    samples=comparisons()
    final=decisions()
    agree=sum(pred==ref for _,pred,ref in samples)
    counts=Counter((pred,ref) for _,pred,ref in samples)
    metrics={label:{'first_reading':sum(n for (p,r),n in counts.items() if p==label),
                    'independent_reading':sum(n for (p,r),n in counts.items() if r==label),
                    'agreed':counts[label,label]} for label in LABELS.values()}
    with (HERE/'validation_results.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['source_url','title','first_reading','independent_reading','applied_scope','basis'])
        for r,pred,ref in samples: w.writerow([r['url'],r['title'],pred,ref,*final[r['url']]])
    (HERE/'metrics.json').write_text(json.dumps(dict(agreement=agree,sample=len(samples),by_label=metrics),indent=2))
    summary=''.join('<tr><td>'+escape(label.replace('_',' '))+'</td>'+''.join('<td>'+str(values[k])+'</td>' for k in ('first_reading','independent_reading','agreed'))+'</tr>' for label,values in metrics.items())
    details=''.join('<tr><td><a href="'+escape(r['url'],quote=True)+'">'+escape(r['title'])+'</a></td>'+''.join('<td>'+escape(value)+'</td>' for value in [pred,ref,*final[r['url']]])+'</tr>' for r,pred,ref in samples)
    (HERE/'audit.html').write_text(f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Scope backlog validation</title>
    <style>body{{margin:4vw;color:#173934;font:16px/1.5 system-ui}}p{{max-width:82ch}}td,th{{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid #ccc}}a{{color:#08645f}}</style>
    <h1>Scope backlog validation</h1><p>Three agents split the 3,505 previously unclear records by URL. Each announcement received one first reading. Reviewers used AWS titles and source text to distinguish a new customer action, an improvement to the same action and an extension to a new target. Commercial, maintenance and product changes retain their own scopes. Unclear remains available for ambiguous or non-product posts.</p>
    <p>A separate reader classified 100 records selected by a seeded URL hash from the entire backlog before seeing the first readings. Agreement was {agree}/100. The table preserves both readings before reconciliation. One of the first-pass readers reconciled disagreements against full source bodies. An additional review covered proposed new products, unclear cases and posts previously tagged unknown or non-product. The random validation decisions take precedence on overlapping records. Other unsampled backlog rows have a single agent reading. This check covers the backlog as a whole and has limited evidence for rare scopes. Close differences in scope counts should be interpreted with this uncertainty.</p>
    <h2>Agreement by scope</h2><table><tr><th>Scope</th><th>First reader</th><th>Independent reader</th><th>Both assigned</th></tr>{summary}</table>
    <h2>Source readings</h2><table><tr><th>Source</th><th>First reading</th><th>Independent reading</th><th>Applied scope</th><th>Basis</th></tr>{details}</table>""")
if __name__=='__main__': report()
