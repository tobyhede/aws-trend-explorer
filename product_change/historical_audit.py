"""Blind reference preparation, frozen scoring and reproducible historical audit."""
import argparse
import csv
import hashlib
import html
import json
import math
from collections import Counter
from pathlib import Path

import duckdb
from historical import HERE, LEVELS, load_initial, read_ratings


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def wilson(correct, total):
    if not total:
        return None
    z = 1.959963984540054
    p = correct / total
    denominator = 1 + z*z/total
    center = (p + z*z/(2*total)) / denominator
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / denominator
    return [center-half, center+half]


def prepare():
    """Does not open initial production ratings; no label leakage into third reading."""
    sample = json.loads((HERE / 'sample.json').read_text())
    a = read_ratings(HERE / 'sample_reader_a.tsv', 200)
    b = read_ratings(HERE / 'sample_reader_b.tsv', 200)
    frozen = json.loads((HERE / 'reader_a_frozen.json').read_text())
    assert digest(HERE / frozen['file']) == frozen['sha256']
    required = {i for i in range(200) if a[i]['level'] != b[i]['level'] or 'low' in (a[i]['confidence'], b[i]['confidence'])}
    agreements = sorted(set(range(200)) - required, key=lambda i: hashlib.sha256(('historical-agreement-check:' + sample[i]['url']).encode()).hexdigest())[:20]
    indices = sorted(required | set(agreements))
    save('third_reading.json', [dict(sample[i], index=j, sample_index=i) for j, i in enumerate(indices)])
    save('reference_protocol.json', {'sample_size': 200, 'reader_a_sha256': digest(HERE/'sample_reader_a.tsv'),
        'reader_b_sha256': digest(HERE/'sample_reader_b.tsv'), 'required_indices': sorted(required),
        'agreement_checks': agreements, 'third_indices': indices,
        'selection': 'All reader disagreements and low-confidence cases, plus 20 deterministic agreement checks; third reader sees source text only.'})
    print('Prepared', len(indices), 'blinded third readings.')


def freeze():
    protocol = json.loads((HERE / 'reference_protocol.json').read_text())
    assert digest(HERE/'sample_reader_a.tsv') == protocol['reader_a_sha256']
    assert digest(HERE/'sample_reader_b.tsv') == protocol['reader_b_sha256']
    read_ratings(HERE/'sample_reader_c.tsv', len(protocol['third_indices']))
    reference = read_ratings(HERE/'reference.tsv', 200)
    sample = json.loads((HERE/'sample.json').read_text())
    save('reference.json', [dict(row, index=i, source_url=sample[i]['url']) for i, row in enumerate(reference)])
    save('reference_frozen.json', {'date':'2026-11-25', 'sample_size':200,
        'reference_sha256':digest(HERE/'reference.json'), 'reference_tsv_sha256':digest(HERE/'reference.tsv'),
        'reader_c_sha256':digest(HERE/'sample_reader_c.tsv'), 'protocol_sha256':digest(HERE/'reference_protocol.json'),
        'context_sha256':digest(HERE/'reference_context.json'), 'adjudication_sha256':digest(HERE/'reference_adjudication.json'),
        'original_reference_sha256':digest(HERE/'reference_v1/reference.json'),
        'reference_type':'Blind AI source readings, adjudicated with official context. One contextual correction followed the first freeze during targeted review; both versions retained. Not human ground truth.'})
    print('Frozen 200-record source reference.')


def score():
    frozen = json.loads((HERE/'reference_frozen.json').read_text())
    for file, key in [('reference.json','reference_sha256'),('reference.tsv','reference_tsv_sha256'),('sample_reader_c.tsv','reader_c_sha256'),('reference_protocol.json','protocol_sha256'),('reference_context.json','context_sha256'),('reference_adjudication.json','adjudication_sha256')]:
        assert digest(HERE/file) == frozen[key], file
    protocol=json.loads((HERE/'reference_protocol.json').read_text())
    for suffix in ['a','b']:
        assert digest(HERE/f'sample_reader_{suffix}.tsv') == protocol[f'reader_{suffix}_sha256']
    with duckdb.connect(str(HERE.parent.parent/'announcements.duckdb'),read_only=True) as db:
        sources, initial=load_initial(db)
    initial_hashes={f'ratings{i}.tsv':digest(HERE/f'ratings{i}.tsv') for i in range(3)}
    if (HERE/'initial_frozen.json').exists():
        assert json.loads((HERE/'initial_frozen.json').read_text())==initial_hashes
    else:
        save('initial_frozen.json',initial_hashes)
    reference=json.loads((HERE/'reference.json').read_text())
    a=read_ratings(HERE/'sample_reader_a.tsv',200)
    b=read_ratings(HERE/'sample_reader_b.tsv',200)
    rows=[]
    for i,ref in enumerate(reference):
        url=ref['source_url']; prediction=initial[url]; source=sources[url]
        rows.append({'index':i,'date':source['date'],'title':source['title'],'source_url':url,
            'initial_level':prediction['level'],'reference_level':ref['level'],
            'reader_a':a[i]['level'],'reader_b':b[i]['level'],
            'exact_match':prediction['level']==ref['level'], 'reference_confidence':ref['confidence'],
            'initial_reason':prediction['reason'],'reference_reason':ref['reason']})
    original_reference=json.loads((HERE/'reference_v1/reference.json').read_text())
    assert digest(HERE/'reference_v1/reference.json') == frozen['original_reference_sha256']
    original_exact=sum(initial[r['source_url']]['level']==r['level'] for r in original_reference)
    reference_revisions=sum(old['level']!=new['level'] for old,new in zip(original_reference,reference))
    exact=sum(r['exact_match'] for r in rows)
    product=[r for r in rows if r['reference_level'] in {'1','2','3','4','5'}]
    product_exact=sum(r['exact_match'] for r in product)
    certain=[r for r in rows if r['reference_level']!='U' and r['reference_confidence']!='low']
    certain_exact=sum(r['exact_match'] for r in certain)
    by_level={}
    for level in ['1','2','3','4','5','U','NA']:
        true_positive=sum(r['initial_level']==r['reference_level']==level for r in rows)
        predicted=sum(r['initial_level']==level for r in rows)
        actual=sum(r['reference_level']==level for r in rows)
        by_level[level]={'correct':true_positive,'predicted':predicted,'reference':actual,
            'precision':true_positive/predicted if predicted else None,
            'recall':true_positive/actual if actual else None}
    metrics={'sample_size':200,'population_size':9247,'original_frozen_reference_exact':original_exact,'original_frozen_reference_agreement':original_exact/200,'contextual_reference_revisions':reference_revisions,'exact_agreement':exact,'agreement_rate':exact/200,
        'wilson_95':wilson(exact,200),'resolved_reference_count':len(certain),'resolved_reference_exact':certain_exact,
        'reference_uncertainty_bounds':[certain_exact/200,(certain_exact+200-len(certain))/200],
        'reference_product_count':len(product),'product_exact':product_exact,
        'product_agreement':product_exact/len(product) if product else None,'product_wilson_95':wilson(product_exact,len(product)),
        'reader_a_b_agreement':sum(x['level']==y['level'] for x,y in zip(a,b)),
        'by_level':by_level,'missed_reference_high_scope':sum(r['reference_level'] in {'4','5'} and r['initial_level'] not in {'4','5'} for r in rows),'reference_low_or_unknown':sum(r['reference_confidence']=='low' or r['reference_level']=='U' for r in rows),
        'confusion':dict(sorted(Counter(r['initial_level']+' -> '+r['reference_level'] for r in rows).items())),
        'by_year':{year:{'sample_size':sum(r['date'].startswith(year) for r in rows),'exact':sum(r['date'].startswith(year) and r['exact_match'] for r in rows)} for year in ['2021','2022','2023','2024']},
        'interpretation':'Agreement against a fresh blinded AI source reference, before corrections; not human-validated accuracy. Wilson intervals describe sample uncertainty only.'}
    save('metrics.json',metrics)
    save('row_audit.json',rows)
    with (HERE/'row_audit.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    cross_review=json.loads((HERE/'cross_review_final.json').read_text())
    targeted={url for url,row in initial.items() if row['level'] in {'4','5'}}
    assert set(cross_review)==targeted, 'Every initial level 4/5 must have a second source reading'
    for url,row in cross_review.items():
        assert row['initial_level']==initial[url]['level'] and row['level'] in LEVELS and row['reason'].strip()
    overrides=json.loads((HERE/'cross_review_overrides.json').read_text())
    assert set(overrides)=={url for url,row in cross_review.items() if row['level']!=initial[url]['level']}
    assert all(overrides[url]['level']==cross_review[url]['level'] and overrides[url]['reason']==cross_review[url]['reason'] for url in overrides)
    assert set(overrides)<=set(sources)
    for url,row in overrides.items():
        assert row['level'] in LEVELS and row['reason'].strip()
    # Sample reference takes precedence; any later reconsideration requires a new audit version.
    for ref in reference:
        url=ref['source_url']
        if initial[url]['level']!=ref['level'] or url in overrides:
            overrides[url]={'level':ref['level'],'reason':ref['reason'],'confidence':ref['confidence']}
    final={url:overrides.get(url,row) for url,row in initial.items()}
    report={'source_records':9247,'sample_size':200,'audit_complete':True,'date':'2026-11-25',
        'targeted_high_scope_reviewed':len(cross_review),
        'cross_review_sha256':digest(HERE/'cross_review_final.json'),
        'counts':dict(sorted(Counter(r['level'] for r in final.values()).items())),
        'initial_counts':dict(sorted(Counter(r['level'] for r in initial.values()).items())),
        'initial_confidence':dict(sorted(Counter(r['confidence'] for r in initial.values()).items())),
        'changed_records':sum(final[url]['level']!=row['level'] for url,row in initial.items()),
        'overrides':overrides,'initial_hashes':initial_hashes,'reference_sha256':frozen['reference_sha256'],
        'metrics_sha256':digest(HERE/'metrics.json')}
    save('final_review.json',report)
    low,high=metrics['wilson_95']
    content=['<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Historical product-change audit</title>',
        '<style>body{max-width:1100px;margin:40px auto;padding:0 20px;font:16px/1.6 system-ui;color:#173934}table{border-collapse:collapse;width:100%}td,th{padding:8px;text-align:left;border-bottom:1px solid #ddd}a{color:#08645f}details{margin:14px 0}</style>',
        '<h1>Historical product-change classification · 2021–2024</h1>',
        '<p>All 9,247 collected historical announcements received individual readings of saved official AWS text. The 4,920 existing 2025–2026 decisions are unchanged. This extends classification coverage; it does not prove the historical source collection is exhaustive.</p>',
        '<p><a href="/historical-audit.csv">Download row-level audit CSV</a> · <a href="/historical-audit-metrics.json">Audit metrics JSON</a></p>',
        '<h2>Fresh sample agreement</h2>',
        f'<p>The initial ratings matched a blinded AI reference on <b>{exact}/200 ({exact/2:.1f}%)</b> announcements; the 95% Wilson interval is {low*100:.1f}–{high*100:.1f}%. These scores are measured before corrections. On reference levels 1–5, agreement is {product_exact}/{len(product)} ({metrics["product_agreement"]*100:.1f}%).</p>',
        f'<p>Two independent readers agreed on {metrics["reader_a_b_agreement"]}/200 ratings. A third source-only reader checked all disagreements and low-confidence cases plus 20 agreements. The adjudicated reference contains {metrics["reference_low_or_unknown"]} unknown or low-confidence cases. The first reference was frozen before targeted review. During that review, an earlier official Wickr preview exposed one mistaken inaugural-launch assumption; its reference changed from 5 to U before sample scoring. The original frozen reference gives {original_exact}/200 agreement, versus {exact}/200 after that contextual correction. Both references are retained. This is AI-reference agreement, not human-validated accuracy; shared interpretation errors remain possible.</p>',
        '<p>The 200 records were selected without replacement by a seeded pseudorandom URL ranking before classification. All four years were eligible. The saved seed, source files, original readings, reference and scoring code allow exact replay. Small level-4/5 samples cannot establish their accuracy.</p>',
        f'<p>If every unknown/low-confidence reference case were judged against versus in favor of the initial classification, agreement would range from {certain_exact/2:.1f}% to {(certain_exact+200-len(certain))/2:.1f}%. This is a reference-uncertainty sensitivity range, not a confidence interval.</p>',
        '<p><strong>Rare-category limitation:</strong> the sample contains two reference level-4 announcements, both missed by the initial ratings, and no reference level-5 announcements. The targeted check of existing high ratings cannot establish recall among lower-rated records. Fine-grained major-expansion and new-product trend claims remain provisional.</p>',
        '<h2>Category results</h2><table><tr><th>Level</th><th>Initial sample</th><th>Reference sample</th><th>Correct</th><th>Precision</th><th>Recall</th></tr>']
    for level,m in by_level.items():
        precision='—' if m['precision'] is None else f'{m["precision"]*100:.1f}%'
        recall='—' if m['recall'] is None else f'{m["recall"]*100:.1f}%'
        content.append(f'<tr><td>{level}</td><td>{m["predicted"]}</td><td>{m["reference"]}</td><td>{m["correct"]}</td><td>{precision}</td><td>{recall}</td></tr>')
    content.extend(['</table><h2>Published historical counts</h2><table><tr><th>Level</th><th>Announcements</th></tr>'])
    for level,n in report['counts'].items():content.append(f'<tr><td>{level}</td><td>{n:,}</td></tr>')
    content.extend([f'</table><p>{report["changed_records"]} initial levels were corrected using the sample reference and targeted cross-review. All {len(cross_review)} initial level-4/5 records received a second source reading. This targeted check addresses overstatement in those categories; it does not measure how many major changes were missed among lower ratings. Corrected-sample agreement is not reported as fresh accuracy. Other historical records retain their initial source readings.</p>',
        '<h2>Interpretation and coverage</h2><p>Levels describe the product change itself, not implementation effort or consequences. Regional, pricing-only and non-product notices are outside scale (NA); U remains unresolved. A post is one observation even when it announces several changes. Annual comparisons use January 1–October 28 for all six years; calendar totals and October 2026 must not be treated as equally complete periods. Service tags overlap. Historical corpus completeness remains based on the existing collection validation and limited AWS roundup spot checks.</p>',
        '<h2>Sample disagreements</h2>'])
    for row in rows:
        if row['exact_match']:continue
        content.append(f'<details><summary>{html.escape(row["date"])} · {html.escape(row["title"])} · {row["initial_level"]} → {row["reference_level"]}</summary><p>Initial: {html.escape(row["initial_reason"])}</p><p>Reference: {html.escape(row["reference_reason"])}</p><a href="{html.escape(row["source_url"],quote=True)}">Official AWS announcement</a></details>')
    (HERE/'report.html').write_text(''.join(content))
    print(json.dumps({k:v for k,v in metrics.items() if k not in {'by_level','confusion'}},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','freeze','score']);args=parser.parse_args()
    {'prepare':prepare,'freeze':freeze,'score':score}[args.action]()
