"""Replay individually reviewed historical source decisions; never infer unread rows."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent / 'historical_review'
LEVELS = {'1', '2', '3', '4', '5', 'NA', 'U'}


def read_ratings(path, size):
    with path.open(newline='') as stream:
        rows = list(csv.reader(stream, delimiter='\t'))
    assert len(rows) == size, (path, len(rows), size)
    result = []
    for index, row in enumerate(rows):
        assert len(row) == 4 and int(row[0]) == index, (path, index, row)
        _, level, reason, confidence = row
        assert level in LEVELS and reason.strip(), (path, index)
        assert confidence in {'high', 'medium', 'low'}, (path, index)
        result.append({'level': level, 'reason': reason, 'confidence': confidence})
    return result


def load_initial(db):
    protocol = json.loads((HERE / 'protocol.json').read_text())
    for name, digest in protocol['source_hashes'].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name
    actual = {url: (str(date), title, text) for url, date, title, text in db.sql(
        "select source_url,announcement_date,title,announcement_text from announcements where announcement_date between '2021-01-01' and '2024-12-31'"
    ).fetchall()}
    sources, ratings = {}, {}
    for batch, size in enumerate(protocol['batch_sizes']):
        rows = json.loads((HERE / f'batch{batch}.json').read_text())
        judgments = read_ratings(HERE / f'ratings{batch}.tsv', size)
        assert len(rows) == size
        for index, (row, judgment) in enumerate(zip(rows, judgments)):
            url = row['url']
            assert row['index'] == index and url not in sources
            assert actual[url] == (row['date'], row['title'], row['text']), url
            sources[url], ratings[url] = row, dict(judgment, batch=batch, index=index)
    assert set(sources) == set(actual) and len(sources) == protocol['records'] == 9247
    sample = json.loads((HERE / 'sample.json').read_text())
    ranked = sorted(sources, key=lambda url: hashlib.sha256((protocol['sample_seed'] + url).encode()).hexdigest())[:protocol['sample_size']]
    assert {r['url'] for r in sample} == set(ranked)
    return sources, ratings


def load_historical(db):
    sources, ratings = load_initial(db)
    review = json.loads((HERE / 'final_review.json').read_text())
    assert review['source_records'] == len(sources)
    assert review['sample_size'] == 200 and review['audit_complete'] is True
    for name, digest in review['initial_hashes'].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name
    assert hashlib.sha256((HERE / 'reference.json').read_bytes()).hexdigest() == review['reference_sha256']
    assert hashlib.sha256((HERE / 'metrics.json').read_bytes()).hexdigest() == review['metrics_sha256']
    assert hashlib.sha256((HERE / 'cross_review_final.json').read_bytes()).hexdigest() == review['cross_review_sha256']
    assert set(review['overrides']) <= set(sources)
    result = {}
    for url, rating in ratings.items():
        final = review['overrides'].get(url, rating)
        assert final['level'] in LEVELS and final['reason'].strip()
        basis = 'historical_source_review_2026-11-25'
        if url in review['overrides']:
            basis += '; adjudicated_source_review'
        result[url] = (final['level'], final['reason'], basis)
    from collections import Counter
    assert dict(Counter(row[0] for row in result.values())) == review['counts']
    return result


def verify_recent_baseline(decisions):
    baseline = json.loads((HERE / 'baseline_decisions.json').read_text())
    mapping = {row[0]: tuple(row[1:]) for row in decisions}
    assert len(baseline) == 4920
    for row in baseline:
        assert mapping[row[0]] == tuple(row[1:]), ('recent rating changed', row[0])
