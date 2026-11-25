"""Score frozen labels against a blind, independently constructed AI reference."""
import csv
import hashlib
import html
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEVELS = ['1','2','3','4','5','NA','U']
NAMES = dict(zip(LEVELS,['Parameter change','Capability refinement','New capability','Major product expansion','New product','Outside scale','Unresolved']))


def readings(name):
    rows=list(csv.reader((HERE/'blind'/name).open(),delimiter='\t'))
    assert len(rows)==200, (name,len(rows))
    result=[]
    for i,r in enumerate(rows):
        assert len(r)==4 and r[0]==str(i) and r[1] in LEVELS and r[3] in ['high','medium','low'] and len(r[2])>12,(name,i,r)
        result.append({'index':i,'level':r[1],'reason':r[2],'confidence':r[3]})
    return result


def wilson(k,n):
    if not n:return None
    z=1.959963984540054;p=k/n;den=1+z*z/n
    centre=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [centre-half,centre+half]


def prepare_adjudication():
    protocol=json.loads((HERE/'protocol.json').read_text())
    sample=json.loads((HERE/'blind/sample.json').read_text())
    a,b=readings('reader_a.tsv'),readings('reader_b.tsv')
    disputed={i for i in range(200) if a[i]['level']!=b[i]['level'] or 'low' in [a[i]['confidence'],b[i]['confidence']]}
    agreements=[i for i in range(200) if i not in disputed]
    controls=sorted(agreements,key=lambda i:hashlib.sha256((protocol['seed']+'agreement-check'+str(i)).encode()).digest())[:20]
    indices=sorted(disputed|set(controls))
    # Third reader receives source only, not labels, selection reason or production predictions.
    path=HERE/'blind/third_sample.json'
    text=json.dumps([sample[i] for i in indices],indent=2)
    if path.exists():assert path.read_text()==text
    else:path.write_text(text)
    manifest={'disputed_or_low_confidence_indices':sorted(disputed),'agreement_check_indices':controls,'third_indices':indices,'reader_agreement':sum(a[i]['level']==b[i]['level'] for i in range(200)),'freeze_hashes':{name:hashlib.sha256((HERE/'blind'/name).read_bytes()).hexdigest() for name in ['reader_a.tsv','reader_b.tsv','third_sample.json']}}
    (HERE/'adjudication_plan.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({k:v for k,v in manifest.items() if k!='freeze_hashes'}))


def score():
    protocol=json.loads((HERE/'protocol.json').read_text())
    for name,digest in protocol['freeze_hashes'].items():assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest,name
    plan=json.loads((HERE/'adjudication_plan.json').read_text())
    for name,digest in plan['freeze_hashes'].items():assert hashlib.sha256((HERE/'blind'/name).read_bytes()).hexdigest()==digest,name
    sample=json.loads((HERE/'blind/sample.json').read_text())
    eligible=json.loads((HERE/'eligible_urls.json').read_text());excluded=set(json.loads((HERE/'excluded_urls.json').read_text()))
    selected=sorted(eligible,key=lambda u:hashlib.sha256((protocol['seed']+u).encode()).digest())[:200]
    assert [r['url'] for r in sample]==selected and not set(selected)&excluded
    a,b=readings('reader_a.tsv'),readings('reader_b.tsv')
    reference=json.loads((HERE/'blind/reference.json').read_text())
    assert len(reference)==200 and [r['index'] for r in reference]==list(range(200))
    refhash=hashlib.sha256((HERE/'blind/reference.json').read_bytes()).hexdigest()
    freeze=json.loads((HERE/'reference_freeze.json').read_text());assert refhash==freeze['sha256']
    for name,digest in freeze['inputs'].items():assert hashlib.sha256((HERE/'blind'/name).read_bytes()).hexdigest()==digest,name
    predicted=json.loads((HERE/'frozen_predictions.json').read_text())
    assert len(sample)==len(predicted)==len(reference)==200
    assert [r['index'] for r in predicted]==list(range(200))
    rows=[]
    for i,(s,p,r) in enumerate(zip(sample,predicted,reference)):
        assert s['url']==p['url'] and r['level'] in LEVELS and r['confidence'] in ['high','medium','low']
        rows.append({'index':i,'date':s['date'],'title':s['title'],'source_url':s['url'],'production_level':p['level'],'reference_level':r['level'],'match':p['level']==r['level'],'reference_confidence':r['confidence'],'reader_a':a[i]['level'],'reader_b':b[i]['level'],'reference_reason':r['reason'],'production_reason':p['reason'],'reference_basis':r['basis']})
    correct=sum(r['match'] for r in rows);confusion=Counter((r['reference_level'],r['production_level']) for r in rows)
    categories=[]
    for level in LEVELS:
        tp=confusion[level,level];n_pred=sum(r['production_level']==level for r in rows);n_ref=sum(r['reference_level']==level for r in rows)
        categories.append({'level':level,'name':NAMES[level],'production_n':n_pred,'reference_n':n_ref,'correct':tp,'precision':tp/n_pred if n_pred else None,'precision_95ci':wilson(tp,n_pred),'recall':tp/n_ref if n_ref else None,'recall_95ci':wilson(tp,n_ref)})
    certain=[r for r in rows if r['reference_confidence']!='low' and r['reference_level']!='U']
    uncertain=[r for r in rows if r not in certain]
    certain_correct=sum(r['match'] for r in certain)
    metrics={**{k:protocol[k] for k in ['date','population','eligible_population','excluded_previous_review','sample_size','scope']},'reference_type':'AI-adjudicated reference; not independently human-validated ground truth','correct':correct,'mismatches':200-correct,'reference_accuracy':correct/200,'wilson_95ci':wilson(correct,200),'reader_agreement_n':plan['reader_agreement'],'reader_agreement':plan['reader_agreement']/200,'third_source_readings':len(plan['third_indices']),'uncertain_reference_n':len(uncertain),'resolved_reference_n':len(certain),'resolved_reference_correct':certain_correct,'resolved_reference_accuracy':certain_correct/len(certain) if certain else None,'uncertainty_sensitivity_bounds':[certain_correct/200,(certain_correct+len(uncertain))/200],'categories':categories,'confusion':[{'reference':a,'production':b,'n':n} for (a,b),n in sorted(confusion.items())],'reference_sha256':refhash,'production_sha256':protocol['freeze_hashes']['frozen_predictions.json'],'limitations':['Estimate applies to 4,578 previously un-audited records, not automatically to all 4,920 classified records.','Prior audits removed most or all existing level-4/5 records; this sample cannot validate those category precisions.','Independent AI readers can share systematic errors. Accuracy here means agreement with an adjudicated AI reference.','Wilson intervals describe sampling uncertainty only, not uncertainty in the reference judgments.','Saved announcement text was used; no fresh AWS retrieval or coverage audit was performed.','Production classifications were frozen before sampling review and have not been corrected as part of this accuracy measurement.']}
    product_rows=[r for r in rows if r['reference_level'] in ['1','2','3','4','5']]
    product_correct=sum(r['match'] for r in product_rows)
    metrics['reference_product_changes']={'n':len(product_rows),'correct':product_correct,'accuracy':product_correct/len(product_rows) if product_rows else None,'wilson_95ci':wilson(product_correct,len(product_rows))}
    metrics['by_year']=[{'year':year,'n':sum(r['date'].startswith(year) for r in rows),'correct':sum(r['match'] and r['date'].startswith(year) for r in rows)} for year in ['2025','2026']]
    (HERE/'metrics.json').write_text(json.dumps(metrics,indent=2))
    (HERE/'row_audit.json').write_text(json.dumps(rows,indent=2))
    for name,data in [('row_audit.csv',rows),('mismatches.csv',[r for r in rows if not r['match']])]:
        with (HERE/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(data)
    e=html.escape;lo,hi=metrics['wilson_95ci']
    page=f'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fresh classification accuracy audit</title><style>body{{font:16px/1.5 system-ui;color:#203a3d;max-width:1150px;margin:40px auto;padding:0 20px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccd6d2;padding:8px;text-align:left}}a{{color:#086c67}}</style><h1>Fresh classification accuracy audit</h1><p>24 November 2026 · 2025–28 October 2026 source window</p><p><strong>{correct}/200 ({correct/200:.1%})</strong> frozen production classifications match the blind adjudicated AI reference. Wilson 95% interval: <strong>{lo:.1%}–{hi:.1%}</strong>.</p><p>Sampling frame: {len(eligible):,} previously un-audited records; {len(excluded)} previously audited records excluded. Two readers independently classified all 200 without production labels. A third reader assessed all disagreements/low-confidence cases and 20 randomly selected agreements. The reference was frozen before scoring.</p><p>Initial reader agreement: {plan["reader_agreement"]}/200 ({plan["reader_agreement"]/200:.1%}). Third-reader source checks: {len(plan["third_indices"])}. Uncertain reference labels: {len(uncertain)}. Production labels remain unchanged.</p>'
    if product_rows:page+=f'<p>For records the reference identifies as product changes (levels 1–5), exact agreement is {product_correct}/{len(product_rows)} ({product_correct/len(product_rows):.1%}). This excludes easy outside-scale cases, but is a conditional estimate.</p>'
    page+=f'<p>Reference-uncertainty sensitivity: if all {len(uncertain)} uncertain reference cases were incorrect versus correct in production, the score would range from {metrics["uncertainty_sensitivity_bounds"][0]:.1%} to {metrics["uncertainty_sensitivity_bounds"][1]:.1%}. This is not a confidence interval.</p>'
    page+='<ul>'+''.join('<li>'+e(x)+'</li>' for x in metrics['limitations'])+'</ul><h2>Category results</h2><p>Precision: correct among production predictions. Recall: correct among reference labels. Small denominators are not reliable category-level estimates.</p><table><tr><th>Category</th><th>Production n</th><th>Reference n</th><th>Correct</th><th>Precision</th><th>Recall</th></tr>'
    for c in categories:
        pct=lambda v:'Not measured' if v is None else f'{v:.1%}'
        page+=f'<tr><td>{e(c["name"])}</td><td>{c["production_n"]}</td><td>{c["reference_n"]}</td><td>{c["correct"]}</td><td>{pct(c["precision"])}</td><td>{pct(c["recall"])}</td></tr>'
    page+='</table><h2>Confusion matrix</h2><p>Rows are reference labels; columns are frozen production labels. These counts apply only to the fresh sampling frame.</p><table><tr><th>Reference / production</th>'+''.join('<th>'+e(level)+'</th>' for level in LEVELS)+'</tr>'
    for reference_level in LEVELS:
        page+='<tr><th>'+e(reference_level)+'</th>'+''.join('<td>'+str(confusion[reference_level,production_level])+'</td>' for production_level in LEVELS)+'</tr>'
    page+='</table><h2>Disagreements with the frozen production labels</h2><p>These are audit findings, not applied corrections.</p><table><tr><th>Announcement</th><th>Production</th><th>Reference</th><th>Reference reasoning</th></tr>'
    for r in rows:
        if not r['match']:page+=f'<tr><td><a href="{e(r["source_url"])}">{e(r["title"])}</a></td><td>{r["production_level"]}</td><td>{r["reference_level"]} ({r["reference_confidence"]})</td><td>{e(r["reference_reason"])}</td></tr>'
    page+='</table>'
    (HERE/'report.html').write_text(page)
    print(json.dumps({k:metrics[k] for k in ['correct','mismatches','reference_accuracy','wilson_95ci','reader_agreement_n','uncertain_reference_n','resolved_reference_accuracy']},indent=2))


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');args=ap.parse_args()
    if args.prepare:prepare_adjudication()
    else:score()
