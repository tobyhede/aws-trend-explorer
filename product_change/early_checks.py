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


@check
def coverage_report_counts_archived_links_absent_from_the_inventory():
    from early_coverage import save_file, report
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_snapshot(root, [
            (2010, 0, [api_item('kept', '2010-02-01', 'Kept', '', '<p>K.</p>'),
                       api_item('Mixed-Case', '2010-12-20', 'Mixed', '', '<p>M.</p>')], 2),
            (2011, 0, [api_item('b', '2011-03-01', 'B', '', '<p>B.</p>')], 1)])
        header = ['timestamp', 'original', 'statuscode', 'length', 'digest']
        cdx = [header, ['20101202112050', 'https://aws.amazon.com/about-aws/whats-new/2010/', '200', '1', 'X'],
               ['20110105000000', 'http://aws.amazon.com/about-aws/whats-new/2010/', '200', '1', 'Y'],
               ['20110110000000', 'https://aws.amazon.com/about-aws/whats-new/2010/', '200', '1', 'Z']]
        save_file(root, 'archive/cdx/2010.json', json.dumps(cdx).encode(), 'https://example.invalid/cdx', '2026-11-27')
        save_file(root, 'archive/cdx/2011.json', json.dumps([header]).encode(), 'https://example.invalid/cdx', '2026-11-27')
        page = ('<a href="/about-aws/whats-new/2010/02/kept/">k</a> <a href="//aws.amazon.com/about-aws/whats-new/2010/12/mixed-case/">m</a>'
                '<a href="https://aws.amazon.com/about-aws/whats-new/2010/06/gone/?nc=1">g</a> <a href="/about-aws/whats-new/2009/01/old/">o</a>'
                '<a href="/about-aws/whats-new/2010/">index</a>')
        save_file(root, 'archive/pages/2010_20110105000000.html', page.encode(), 'https://example.invalid/page', '2026-11-27')
        result = report(root, [2010, 2011])
    year2010, year2011 = result['years']
    assert year2010['status'] == 'checked' and year2010['capture'] == '20110105000000', year2010
    assert year2010['capture_date'] == '2011-01-05'
    assert (year2010['archived_links'], year2010['inventory'], year2010['absent_count']) == (3, 2, 1), year2010
    assert year2010['absent'] == ['https://aws.amazon.com/about-aws/whats-new/2010/06/gone/']
    assert year2011['status'] == 'unchecked' and year2011['absent_count'] is None and year2011['inventory'] == 1, year2011


def corpus(populations):
    return [{'announcement_date': f'{year}-06-01', 'source_url': f'https://aws.amazon.com/about-aws/whats-new/{year}/06/r{i}/',
             'title': f'T{i}', 'announcement_text': f'Text {i}.', 'service': 'unknown'} for year, n in populations.items() for i in range(n)]


@check
def hidden_sample_has_a_floor_per_year_and_the_rest_proportional():
    from early_samples import draw_hidden
    records = corpus({2010: 30, 2011: 100, 2012: 870})
    sample = draw_hidden(records, 'seed-a', size=100, floor=20)
    by_year = {y: sum(r['date'].startswith(str(y)) for r in sample) for y in (2010, 2011, 2012)}
    # floor 60, remainder 40 split 1.2 / 4 / 34.8, the largest remainder going to 2012
    assert by_year == {2010: 21, 2011: 24, 2012: 55}, by_year
    assert len({r['url'] for r in sample}) == 100
    assert [r['index'] for r in sample] == list(range(100))
    assert set(sample[0]) == {'index', 'date', 'url', 'title', 'text'}
    assert draw_hidden(records, 'seed-a', size=100, floor=20) == sample
    assert draw_hidden(records, 'seed-b', size=100, floor=20) != sample


@check
def bridge_sample_draws_two_hundred_per_earlier_pass_without_labels():
    from early_samples import draw_bridge
    recent = [{'date': '2025-01-01', 'url': f'https://x/r{i}', 'title': 't', 'text': 'x', 'level': '3', 'reason': 'r'} for i in range(500)]
    older = [{'date': '2022-01-01', 'url': f'https://x/o{i}', 'title': 't', 'text': 'x', 'level': '2', 'reason': 'r'} for i in range(900)]
    sample = draw_bridge({'2025-2026': recent, '2021-2024': older}, 'seed-a', size=200)
    assert [sum(r['pass'] == p for r in sample) for p in ('2025-2026', '2021-2024')] == [200, 200]
    assert all(set(r) == {'index', 'pass', 'date', 'url', 'title', 'text'} for r in sample)
    assert draw_bridge({'2025-2026': recent, '2021-2024': older}, 'seed-a', size=200) == sample


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
