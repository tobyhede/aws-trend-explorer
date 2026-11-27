"""Offline checks for the 2010–2020 extension: no network, no API key.

Run from the repository root: .venv/bin/python product_change/early_checks.py
"""
import json
import tempfile
import traceback
from pathlib import Path

CHECKS = []


def check(function):
    CHECKS.append(function)
    return function


def api_item(slug, date, headline, summary, body, products=()):
    tags = [{'id': f'whats-new-v2#year#{date[:4]}'}, {'id': 'GLOBAL#content-type#launch-announcement'}]
    tags += [{'id': f'whats-new-v2#general-products#{p}'} for p in products]
    path = f'/about-aws/whats-new/{date[:4]}/{date[5:7]}/{slug}/'
    return {'item': {'id': 'whats-new-v2#' + path.strip('/').replace('/', '-'), 'additionalFields': {
        'headlineUrl': path, 'postDateTime': date + 'T20:00:00Z', 'headline': headline,
        'postSummary': summary, 'postBody': body}}, 'tags': tags}


def write_snapshot(root, pages):
    """Save canned API pages and a manifest as the collector would."""
    from early_collect import save_page
    for year, page, items, total in pages:
        save_page(root, year, page, json.dumps({'items': items, 'metadata': {'count': len(items), 'totalHits': total}}).encode(), 'https://example.invalid/', '2026-11-27')


@check
def parsing_yields_corpus_fields_from_saved_responses():
    from early_collect import parse
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_snapshot(root, [(2010, 0, [
            api_item('s3-versioning', '2010-02-08', 'Amazon S3 Versioning ', '<p>Versioning is <a href="/x">now</a> available.&nbsp;</p>',
                     '<p>Versioning is <a href="https://aws.amazon.com/s3/">now</a> available.</p>\n<p>Keep <b>every</b> version.</p>', ['aws-cli', 'amazon-s3']),
            api_item('lower-prices', '2010-02-01', 'Lower Prices', '', '<p>Prices fall.</p>'),
        ], 2)])
        records = parse(root)
    assert [r['source_url'] for r in records] == [
        'https://aws.amazon.com/about-aws/whats-new/2010/02/lower-prices/',
        'https://aws.amazon.com/about-aws/whats-new/2010/02/s3-versioning/'], records
    first, second = records
    assert second['announcement_date'] == '2010-02-08'
    assert second['title'] == 'Amazon S3 Versioning'
    assert second['announcement_text'] == 'Versioning is now available. Versioning is now available. Keep every version.', second['announcement_text']
    assert second['service'] == 'amazon-s3; aws-cli'
    assert second['source_id'] == 'whats-new-v2#about-aws-whats-new-2010-02-s3-versioning'
    assert second['source_snapshot'] == 'raw/2010_p0000.json'
    assert second['record_origin'] == 'directory snapshot'
    assert second['text_source_url'] == second['source_url']
    assert first['service'] == 'unknown'
    assert first['announcement_text'] == 'Prices fall.'
    assert first['primary_scope'] is None and first['magnitude'] is None and first['product_change_level'] is None


@check
def collection_resumes_from_saved_pages_and_check_runs_offline():
    from early_collect import collect, check as check_snapshot
    item = api_item('a', '2011-03-01', 'A', '', '<p>A.</p>')
    calls = []

    def fetch(url):
        calls.append(url)
        if 'year%232012' in url and len(calls) == 2:
            raise OSError('connection dropped')
        year = '2011' if 'year%232011' in url else '2012'
        return json.dumps({'items': [api_item('b' + year, f'{year}-05-01', 'B', '', '<p>B.</p>')], 'metadata': {'totalHits': 1}}).encode()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            collect(root, [2011, 2012], fetch=fetch, delay=0)
            raise AssertionError('a dropped connection should stop the run')
        except OSError:
            pass
        assert len(calls) == 2 and (root / 'raw/2011_p0000.json').exists()
        collect(root, [2011, 2012], fetch=fetch, delay=0)
        assert len(calls) == 3 and 'year%232012' in calls[-1], calls  # 2011 was not fetched again
        assert check_snapshot(root) == {2011: 1, 2012: 1}
        manifest = json.loads((root / 'manifest.json').read_text())
        assert {p['collected'] for p in manifest['pages']} and all(len(p['sha256']) == 64 for p in manifest['pages'])

        (root / 'raw/2011_p0000.json').write_bytes(json.dumps({'items': [item, item], 'metadata': {'totalHits': 1}}).encode())
        try:
            check_snapshot(root)
            raise AssertionError('an edited raw response must fail the check')
        except AssertionError as error:
            assert 'changed since collection' in str(error), error


@check
def check_fails_when_parsed_count_differs_from_listed_count():
    from early_collect import check as check_snapshot
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_snapshot(root, [(2010, 0, [api_item('a', '2010-01-05', 'A', '', '<p>A.</p>')], 2)])
        try:
            check_snapshot(root)
            raise AssertionError('a short listing must fail the check')
        except AssertionError as error:
            assert 'API listed' in str(error), error


@check
def records_dated_outside_their_year_tag_are_set_aside_and_reported():
    from early_collect import parse, misdated, check as check_snapshot
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_snapshot(root, [(2016, 0, [api_item('a', '2016-01-05', 'A', '', '<p>A.</p>'),
                                         api_item('late', '2026-04-29', 'Late', '', '<p>L.</p>')], 2)])
        assert [r['title'] for r in parse(root)] == ['A']
        assert [(r['year_tag'], r['announcement_date']) for r in misdated(root)] == [(2016, '2026-04-29')]
        assert check_snapshot(root) == {2016: 2}


def main():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    failed = 0
    for function in CHECKS:
        try:
            function()
            print('ok  ', function.__name__)
        except Exception:
            failed += 1
            print('FAIL', function.__name__)
            traceback.print_exc()
    print(f'{len(CHECKS) - failed}/{len(CHECKS)} checks passed')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
