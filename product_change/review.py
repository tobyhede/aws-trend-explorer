"""Replay individually recorded source readings; no text-based inference or label fallback."""
import csv
import hashlib
import html
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / 'source_review'
LEVELS = {'1', '2', '3', '4', '5', 'NA', 'U'}


def read_ratings(path, size):
    rows = list(csv.reader(path.open(), delimiter='\t'))
    if len(rows) != size:
        raise ValueError(f'{path.name}: expected {size} readings, found {len(rows)}')
    result = []
    for index, row in enumerate(rows):
        if len(row) != 3 or row[0] != str(index) or row[1] not in LEVELS or len(row[2].strip()) < 12:
            raise ValueError(f'{path.name}: invalid reading at {index}: {row}')
        result.append((row[1], row[2]))
    return result


def load_review(expected_rows, agreed):
    """Require an exact source match before accepting a replayed classification."""
    expected = {r[0]: (r[-2], r[-1]) for r in expected_rows}
    if len(expected) != 4920 or len(expected_rows) != 4920:
        raise ValueError('Expected exactly 4,920 unique scoped source records')
    sources, initial, final = {}, {}, {}
    hashes = {}
    for batch in range(3):
        path = ROOT / f'batch{batch}.json'
        rows = json.loads(path.read_text())
        ratings_path = ROOT / f'ratings{batch}.tsv'
        ratings = read_ratings(ratings_path, 1640)
        if len(rows) != 1640:
            raise ValueError(f'Batch {batch} source count changed')
        for row, (level, reason) in zip(rows, ratings):
            url = row['url']
            if url in sources or expected.get(url) != (row['title'], row['text']):
                raise ValueError(f'Duplicate or changed source: {url}')
            sources[url] = row
            initial[url] = (level, reason, f'AWS source reading; batch {batch}')
        for file in [path, ratings_path]:
            hashes[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    if set(sources) != set(expected):
        raise ValueError('Source review does not cover the exact database cohort')
    high_audit={}
    for name in ['high_audit1.json','high_audit2.json']:
        part=json.loads((ROOT/name).read_text())
        if set(high_audit)&set(part):raise ValueError('Duplicate high-level audit')
        high_audit.update(part)
    if set(high_audit)!={u for u,v in initial.items() if v[0] in {'4','5'}}:
        raise ValueError('High-level cross-review coverage mismatch')
    final.update(initial)
    for url, (level, reason) in agreed.items():
        final[url] = (level, reason, 'Agreed rubric example; source reviewed')
    adjudications = json.loads((ROOT / 'adjudications.json').read_text())
    for url, decision in adjudications.items():
        level, reason = decision['level'], decision['reason']
        if url not in sources or level not in LEVELS or len(reason) < 12:
            raise ValueError(f'Invalid adjudication: {url}')
        if url in agreed and agreed[url][0] != level:
            raise ValueError(f'Adjudication conflicts with agreed example: {url}')
        final[url] = (level, reason, 'Source adjudication; ' + decision['review'])
    sample = json.loads((ROOT / 'sample.json').read_text())
    ordered = sorted(sources, key=lambda u: hashlib.sha256(('product-change-full-review-validation-01' + u).encode()).hexdigest())[:120]
    if [r['url'] for r in sample] != ordered:
        raise ValueError('Seeded audit sample has changed')
    independent = read_ratings(ROOT / 'sample_reading.tsv', 120)
    audit_rows = []
    for row, (second, reason) in zip(sample, independent):
        url = row['url']
        first = initial[url][0]
        if first != second and url not in adjudications:
            raise ValueError(f'Unresolved independent sample disagreement: {url}')
        audit_rows.append({'source_url': url, 'title': row['title'], 'first_level': first,
                           'independent_level': second, 'final_level': final[url][0],
                           'independent_reason': reason, 'final_reason': final[url][1]})
    previous = {r['source_url']: r['product_change_level'] for r in json.loads((ROOT / 'previous_decisions.json').read_text())}
    if set(previous) != set(final):
        raise ValueError('Previous decision snapshot does not cover current cohort')
    confusion = Counter((r['first_level'], r['independent_level']) for r in audit_rows)
    report = {
        'date': '2026-11-24', 'cohort_start': '2025-01-01', 'cohort_end': '2026-10-28',
        'source_records': len(final), 'source_method': 'AI readers evaluated saved AWS announcement text; no fresh page fetch in this pass.',
        'changed_from_previous': sum(previous[u] != v[0] for u, v in final.items()),
        'counts': dict(sorted(Counter(v[0] for v in final.values()).items())),
        'high_level_second_readings':len(high_audit),
        'targeted_interface_readings':len(json.loads((ROOT/'interface_audit.json').read_text())),
        'targeted_commercial_readings':len(json.loads((ROOT/'commercial_audit0.json').read_text()))+1,
        'sample_size': len(sample), 'independent_exact_agreement': sum(r['first_level'] == r['independent_level'] for r in audit_rows),
        'sample_confusion': [{'first': a, 'independent': b, 'n': n} for (a, b), n in sorted(confusion.items())],
        'source_hashes': hashes,
        'final_overrides': [{'source_url': u, 'title': sources[u]['title'], 'first_level': initial[u][0], 'final_level': v[0], 'reason': v[1], 'basis': v[2]} for u, v in final.items() if initial[u] != v],
        'transitions': [{'before': a, 'after': b, 'n': n} for (a, b), n in sorted(Counter((previous[u], v[0]) for u, v in final.items()).items())],
        'limitations': ['Independent agreement measures consistency, not proven accuracy.', 'The 120-record sample is uniform, not a per-category accuracy study; rare levels have few examples.', 'One initial source reader per record; targeted adjudication does not establish error-free classification.', 'The source review does not extend product-change ratings to 2021–2024 or independently establish completeness of AWS source collection.', 'Each announcement receives its highest substantive product-change level; preview and GA are assessed for the change announced and are not deduplicated into unique product launches.']
    }
    for name in ['sample.json', 'sample_reading.tsv', 'adjudications.json', 'previous_decisions.json', 'high_audit1.json', 'high_audit2.json', 'commercial_audit0.json', 'interface_audit.json']:
        report['source_hashes'][name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    changes=[{'source_url': u, 'title': sources[u]['title'], 'previous_level': previous[u], 'first_source_level': initial[u][0], 'final_level': v[0], 'reason': v[1], 'basis': v[2]} for u,v in final.items() if previous[u]!=v[0]]
    with (HERE / 'changes.csv').open('w', newline='') as f:
        w=csv.DictWriter(f,fieldnames=['source_url','title','previous_level','first_source_level','final_level','reason','basis']);w.writeheader();w.writerows(changes)
    (HERE / 'review_report.json').write_text(json.dumps(report, indent=2))
    (HERE / 'sample_audit.json').write_text(json.dumps(audit_rows, indent=2))
    with (HERE / 'sample_audit.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(audit_rows[0])); w.writeheader(); w.writerows(audit_rows)
    e = html.escape
    sections = '<h2>Final category counts</h2><table><tr><th>Level</th><th>Count</th></tr>' + ''.join(f'<tr><td>{e(k)}</td><td>{n}</td></tr>' for k, n in report['counts'].items()) + '</table>'
    sections += '<h2>Independent sample: frozen readings</h2><p>Disagreements are resolved in the final column; agreement below is measured before reconciliation.</p><table><tr><th>Announcement</th><th>First</th><th>Independent</th><th>Final</th><th>Final reason</th></tr>'
    sections += ''.join(f'<tr><td><a href="{e(r["source_url"])}">{e(r["title"])}</a></td><td>{r["first_level"]}</td><td>{r["independent_level"]}</td><td>{r["final_level"]}</td><td>{e(r["final_reason"])}</td></tr>' for r in audit_rows) + '</table>'
    agreement = report['independent_exact_agreement']
    page = '<!doctype html><meta charset="utf-8"><title>Product-change source review</title><style>body{font:16px system-ui;max-width:1150px;margin:40px auto;padding:0 20px;color:#203a3d}table{border-collapse:collapse;width:100%}td,th{padding:8px;border:1px solid #ccd6d2;text-align:left}a{color:#086c67}</style><h1>Product-change source review</h1>'
    page += f'<p>2026-11-24. All 4,920 announcements in the 2025–2026 scope window received individual readings of saved AWS source text. {report["changed_from_previous"]:,} levels changed from the provisional mapping.</p><p>Independent sample agreement: {agreement}/120 ({agreement/120:.1%}) before adjudication. Source files, frozen first readings, the independent sample and all adjudications are included for reproducibility.</p>'
    page += f'<p>Additional checks: all {len(high_audit)} initial level-4/5 decisions received a second-reader source review; {report["targeted_interface_readings"]} search/export/metric refinements and {report["targeted_commercial_readings"]} billing/performance cases received targeted rereadings. Targeted checks are not random accuracy estimates. Final adjudication can differ from either reader.</p>'
    page += '<ul>' + ''.join('<li>' + e(x) + '</li>' for x in report['limitations']) + '</ul>' + sections
    (HERE / 'review.html').write_text(page)
    return final
