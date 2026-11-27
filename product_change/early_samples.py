"""Draw and freeze the hidden sample and the bridge sample before any 2010–2020 reading.

draw   run once, before labelling: picks a fresh seed, draws both samples and writes them with a protocol
       record. It refuses to run if a protocol exists. Like historical_audit.py prepare and freeze, it is
       not part of reproduction; rerunning it with a new seed would destroy the audit's independence.
check  offline: source hashes are unchanged and the saved seed draws exactly the saved samples.

Both samples rank records by SHA-256 of seed plus source URL, as the historical audit does.
Hidden sample: 300 of the 2010–2020 records, at least 20 from each year, the rest allocated in proportion
to each year's records by largest remainder. Bridge sample: 200 records from each earlier labelling pass,
2025–2026 and 2021–2024, with reader inputs only (no recorded level, reason or basis).
"""
import argparse
import hashlib
import json
import secrets
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEW = HERE / 'early_review'
HIDDEN_SIZE, FLOOR, BRIDGE_SIZE = 300, 20, 200
PASSES = {'2025-2026': HERE / 'source_review', '2021-2024': HERE / 'historical_review'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def ranked(urls, seed):
    return sorted(urls, key=lambda url: digest((seed + url).encode()))


def allocate(populations, size, floor):
    """Floor per stratum, remainder in proportion to stratum size by largest remainder."""
    total = sum(populations.values())
    assert all(n >= floor for n in populations.values()) and size >= floor * len(populations)
    remainder = size - floor * len(populations)
    shares = {k: remainder * n / total for k, n in populations.items()}
    allocation = {k: floor + int(s) for k, s in shares.items()}
    for k in sorted(shares, key=lambda k: (int(shares[k]) - shares[k], k))[:size - sum(allocation.values())]:
        allocation[k] += 1
    return allocation


def reader_input(index, date_, url, title, text, **extra):
    return {'index': index, **extra, 'date': date_, 'url': url, 'title': title, 'text': text}


def draw_hidden(records, seed, size=HIDDEN_SIZE, floor=FLOOR):
    by_year = defaultdict(dict)
    for r in records:
        by_year[r['announcement_date'][:4]][r['source_url']] = r
    allocation = allocate({y: len(rows) for y, rows in by_year.items()}, size, floor)
    chosen = [by_year[y][url] for y in sorted(by_year) for url in ranked(by_year[y], seed)[:allocation[y]]]
    chosen.sort(key=lambda r: (r['announcement_date'], r['source_url']))
    return [reader_input(i, r['announcement_date'], r['source_url'], r['title'], r['announcement_text']) for i, r in enumerate(chosen)]


def draw_bridge(passes, seed, size=BRIDGE_SIZE):
    sample = []
    for name, rows in passes.items():
        by_url = {r['url']: r for r in rows}
        assert len(by_url) == len(rows)
        chosen = sorted((by_url[u] for u in ranked(by_url, seed)[:size]), key=lambda r: (r['date'], r['url']))
        sample.extend(dict(r, name=name) for r in chosen)
    return [reader_input(i, r['date'], r['url'], r['title'], r['text'], **{'pass': r['name']}) for i, r in enumerate(sample)]


def earlier_passes():
    """Reader inputs of both earlier passes, from their saved batches; dates for 2025–2026 come from the database."""
    import duckdb
    with duckdb.connect(str(HERE.parent / 'announcements.duckdb'), read_only=True) as db:
        dates = dict(db.sql("select source_url, cast(announcement_date as varchar) from announcements").fetchall())
    passes, files = {}, {}
    for name, folder in PASSES.items():
        rows = []
        for path in sorted(folder.glob('batch[0-9].json')):
            files[str(path.relative_to(HERE))] = digest(path.read_bytes())
            rows += [{'date': dates[r['url']], 'url': r['url'], 'title': r['title'], 'text': r['text']} for r in json.loads(path.read_text())]
        passes[name] = rows
    assert [len(p) for p in passes.values()] == [4920, 9247], [len(p) for p in passes.values()]
    return passes, files


def sources():
    from early_collect import SNAPSHOT, parse
    passes, files = earlier_passes()
    files['early_snapshot/manifest.json'] = digest((SNAPSHOT / 'manifest.json').read_bytes())
    return parse(), passes, files


def save(name, value):
    REVIEW.mkdir(exist_ok=True)
    (REVIEW / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def draw():
    if (REVIEW / 'sample_protocol.json').exists():
        raise SystemExit('sample_protocol.json exists: the samples are drawn once. Use check.')
    records, passes, files = sources()
    seed = secrets.token_hex(24)
    hidden, bridge = draw_hidden(records, seed), draw_bridge(passes, seed)
    save('hidden_sample.json', hidden)
    save('bridge_sample.json', bridge)
    save('sample_protocol.json', {
        'date': date.today().isoformat(), 'seed': seed, 'method': __doc__.split('\n\n', 1)[1].split('\n\n', 1)[1].strip(),
        'hidden_size': HIDDEN_SIZE, 'hidden_floor_per_year': FLOOR, 'bridge_size_per_pass': BRIDGE_SIZE,
        'population': len(records), 'hidden_by_year': {y: sum(r['date'].startswith(y) for r in hidden) for y in sorted({r['date'][:4] for r in hidden})},
        'source_hashes': files, 'hidden_sha256': digest((REVIEW / 'hidden_sample.json').read_bytes()),
        'bridge_sha256': digest((REVIEW / 'bridge_sample.json').read_bytes())})
    check()


def check():
    protocol = json.loads((REVIEW / 'sample_protocol.json').read_text())
    records, passes, files = sources()
    assert files == protocol['source_hashes'], 'a sample source changed since the draw'
    for name, key in [('hidden_sample.json', 'hidden_sha256'), ('bridge_sample.json', 'bridge_sha256')]:
        assert digest((REVIEW / name).read_bytes()) == protocol[key], f'{name} changed since the draw'
    assert json.loads((REVIEW / 'hidden_sample.json').read_text()) == draw_hidden(records, protocol['seed'])
    assert json.loads((REVIEW / 'bridge_sample.json').read_text()) == draw_bridge(passes, protocol['seed'])
    print('Samples verified: hidden', protocol['hidden_by_year'], f'= {protocol["hidden_size"]};', f'bridge {BRIDGE_SIZE} per pass.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=['draw', 'check'])
    {'draw': draw, 'check': check}[parser.parse_args().action]()
