"""The maintainer's check of 40 records labelled level 4 or 5 in 2010–2020.

draw    run once: picks a seed, ranks the level 4 and 5 records by SHA-256 of seed plus URL, and writes
        early_review/human_check/: protocol.json, sample.json, records.md (title, date, URL, text and final label
        to read) and readings.tsv for the maintainer to fill in. It refuses to run if protocol.json exists.
report  offline: counts the maintainer's agree and disagree marks and writes result.json. It refuses to report
        until every record is marked agree or disagree.

The readings are the maintainer's, saved as evidence and reported apart from the AI agreement figures. A label
the maintainer wants changed goes into product_change/audit_corrections.json, where the build applies it and the
saved readings keep the original prediction.
"""
import argparse
import csv
import hashlib
import json
import secrets
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK = HERE / 'early_review' / 'human_check'
SIZE = 40
MARKS = {'agree', 'disagree'}


def draw(final, seed, size=SIZE):
    """final: {url: row with date, title, text, level, reason}. The size records at level 4 or 5 ranked first by seed."""
    candidates = sorted(url for url, row in final.items() if row['level'] in {'4', '5'})
    chosen = sorted(candidates, key=lambda url: hashlib.sha256((seed + url).encode()).hexdigest())[:size]
    rows = [dict(final[url], url=url) for url in chosen]
    rows.sort(key=lambda r: (r['date'], r['url']))
    return [{'index': i, 'date': r['date'], 'url': r['url'], 'title': r['title'], 'text': r['text'], 'level': r['level'],
             'reason': r['reason'], 'basis': r['basis']} for i, r in enumerate(rows)]


def score_readings(sample, readings):
    """readings: {url: (mark, note)}. Every sampled record must be marked agree or disagree."""
    missing = [r['url'] for r in sample if r['url'] not in readings]
    invalid = [url for url, (mark, _) in readings.items() if mark not in MARKS]
    if missing or invalid:
        raise ValueError(f'{len(missing)} records unmarked; invalid marks on {invalid[:5]}')
    agree = sum(readings[r['url']][0] == 'agree' for r in sample)
    return {'read': len(sample), 'agree': agree, 'disagree': len(sample) - agree,
            'by_level': {level: {'read': sum(r['level'] == level for r in sample),
                                 'agree': sum(r['level'] == level and readings[r['url']][0] == 'agree' for r in sample)} for level in ('4', '5')},
            'disagreements': [{'url': r['url'], 'title': r.get('title'), 'level': r['level'], 'note': readings[r['url']][1]}
                              for r in sample if readings[r['url']][0] == 'disagree'],
            'interpretation': ('The maintainer read these records and marked whether they agree with the final level. This human '
                               'check is reported separately from the AI agreement figures and is not combined with them.')}


def early_final():
    final = {}
    for path in sorted((HERE / 'early_review' / 'labels').glob('*/final.json')):
        inputs = {row['url']: row for row in json.loads((path.parent / 'inputs.json').read_text())}
        for url, row in json.loads(path.read_text()).items():
            final[url] = dict(row, date=inputs[url]['date'], title=inputs[url]['title'], text=inputs[url]['text'])
    return final


def write_draw():
    if (CHECK / 'protocol.json').exists():
        raise SystemExit('protocol.json exists: the human check is drawn once. Use report.')
    final = early_final()
    seed = secrets.token_hex(24)
    sample = draw(final, seed)
    CHECK.mkdir(parents=True, exist_ok=True)
    (CHECK / 'sample.json').write_text(json.dumps(sample, indent=1, ensure_ascii=False) + '\n')
    (CHECK / 'protocol.json').write_text(json.dumps({
        'date': date.today().isoformat(), 'seed': seed, 'size': SIZE, 'population': sum(r['level'] in {'4', '5'} for r in final.values()),
        'method': 'SHA-256 of seed plus URL ranks the 2010–2020 records whose final level is 4 or 5; the first 40 are read.',
        'sample_sha256': hashlib.sha256((CHECK / 'sample.json').read_bytes()).hexdigest()}, indent=2) + '\n')
    lines = ['# Maintainer check: 40 records at level 4 or 5, 2010–2020', '',
             'For each record, read the text and decide whether you agree with the final level. Mark `agree` or `disagree` in '
             'readings.tsv, with an optional note. Level 4 is a major product expansion: a substantial subsystem or a new execution, '
             'operating or programming model. Level 5 is a new product: a distinct offering customers can adopt.', '']
    for r in sample:
        lines += [f'## {r["index"]}. {r["title"]}', '', f'{r["date"]} · <{r["url"]}>', '', f'**Final level {r["level"]}.** {r["reason"]}', '', r['text'], '']
    (CHECK / 'records.md').write_text('\n'.join(lines))
    with (CHECK / 'readings.tsv').open('w', newline='') as stream:
        writer = csv.writer(stream, delimiter='\t')
        writer.writerow(['index', 'url', 'level', 'reading', 'note'])
        writer.writerows([[r['index'], r['url'], r['level'], '', ''] for r in sample])
    print(f'Drew {len(sample)} records into {CHECK}; read records.md and fill in readings.tsv.')


def report():
    protocol = json.loads((CHECK / 'protocol.json').read_text())
    assert hashlib.sha256((CHECK / 'sample.json').read_bytes()).hexdigest() == protocol['sample_sha256'], 'sample.json changed since the draw'
    sample = json.loads((CHECK / 'sample.json').read_text())
    with (CHECK / 'readings.tsv').open(newline='') as stream:
        readings = {row['url']: (row['reading'].strip().lower(), row['note'].strip()) for row in csv.DictReader(stream, delimiter='\t')}
    result = score_readings(sample, readings)
    (CHECK / 'result.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(f'Maintainer agreed with {result["agree"]} of {result["read"]} level 4–5 labels; disagreed with {result["disagree"]}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=['draw', 'report'])
    {'draw': write_draw, 'report': report}[parser.parse_args().action]()
