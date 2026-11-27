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


class CannedClient:
    """Stands in for the Claude API. policy(role, records, call_number) returns the reply text."""

    def __init__(self, policy):
        self.policy, self.calls = policy, []

    def complete(self, model, system, user):
        records = json.loads(user)
        role = 'adjudicator' if 'reader_a' in user else 'reader'
        self.calls.append({'model': model, 'system': system, 'user': user, 'role': role})
        return {'text': self.policy(role, records, len(self.calls)), 'model': model, 'stop_reason': 'end_turn'}


def reply(records, level='2', reason='Adds an option to an existing operation.', confidence='high', skip=0):
    return json.dumps({'ratings': [{'index': r['index'], 'level': level, 'reason': reason, 'confidence': confidence} for r in records[skip:]]})


def label_records(n):
    return [{'announcement_date': f'2010-01-{i % 28 + 1:02d}', 'source_url': f'https://aws.amazon.com/about-aws/whats-new/2010/01/r{i:02d}/',
             'title': f'Record {i}', 'announcement_text': f'Amazon Example service now lets customers choose option number {i} for every widget they run today.',
             'service': 'unknown'} for i in range(n)]


@check
def a_reply_missing_a_record_is_rejected_and_asked_again():
    from early_label import label
    first_call = {}

    def policy(role, records, call):
        if not first_call:
            first_call['seen'] = True
            return reply(records, skip=1)
        return reply(records)

    client = CannedClient(policy)
    with tempfile.TemporaryDirectory() as tmp:
        final = label(label_records(30), Path(tmp), client)
        chunk = json.loads((Path(tmp) / 'reader_a/chunk000.json').read_text())
    assert len(client.calls) == 5, len(client.calls)  # two chunks per reader, one re-ask
    assert len(chunk['attempts']) == 2 and 'missing' in chunk['attempts'][0]['rejected'], chunk['attempts'][0]
    assert chunk['model'] == 'claude-fable-5-2' and all(a['model'] == 'claude-fable-5-2' for a in chunk['attempts'])
    assert len(final) == 30 and {r['level'] for r in final.values()} == {'2'}


@check
def a_level_outside_the_scale_or_a_copied_reason_is_rejected():
    from early_label import label
    bad = iter([lambda r: reply(r, level='6'),
                lambda r: reply(r, reason='now lets customers choose option number 0 for every widget'),
                lambda r: reply(r)])
    pending = {'n': 0}

    def policy(role, records, call):
        pending['n'] += 1
        return next(bad)(records) if pending['n'] <= 3 else reply(records)

    with tempfile.TemporaryDirectory() as tmp:
        label(label_records(1), Path(tmp), CannedClient(policy))
        attempts = json.loads((Path(tmp) / 'reader_a/chunk000.json').read_text())['attempts']
    assert [a['rejected'] is not None for a in attempts] == [True, True, False], attempts
    assert 'outside' in attempts[0]['rejected'] and 'copies' in attempts[1]['rejected'], attempts


@check
def a_rerun_skips_saved_chunks():
    from early_label import label
    with tempfile.TemporaryDirectory() as tmp:
        first = CannedClient(lambda role, records, call: reply(records))
        saved = label(label_records(30), Path(tmp), first)
        again = CannedClient(lambda role, records, call: reply(records, level='5'))
        assert label(label_records(30), Path(tmp), again) == saved
    assert len(first.calls) == 4 and again.calls == []


@check
def readers_never_share_a_context_and_a_disagreement_is_adjudicated():
    from early_label import label

    def policy(role, records, call):
        if role == 'adjudicator':
            return reply(records, level='3', reason='A distinct new operation appears in the service.')
        # reader B differs on record 0 only
        if call == 2:
            return json.dumps({'ratings': [{'index': r['index'], 'level': '1' if r['index'] == 0 else '2',
                                            'reason': 'Changes a supported value.', 'confidence': 'medium'} for r in records]})
        return reply(records)

    client = CannedClient(policy)
    with tempfile.TemporaryDirectory() as tmp:
        final = label(label_records(3), Path(tmp), client)
    readers = [c for c in client.calls if c['role'] == 'reader']
    assert len(readers) == 2 and all('Adds an option' not in c['user'] and 'supported value' not in c['user'] for c in readers)
    adjudications = [c for c in client.calls if c['role'] == 'adjudicator']
    assert len(adjudications) == 1
    shown = json.loads(adjudications[0]['user'])
    assert [r['index'] for r in shown] == [0] and shown[0]['reader_a']['level'] == '2' and shown[0]['reader_b']['level'] == '1'
    assert shown[0]['text'] and shown[0]['reader_b']['reason'] == 'Changes a supported value.'
    first = final['https://aws.amazon.com/about-aws/whats-new/2010/01/r00/']
    assert first['level'] == '3' and first['reader_a']['level'] == '2' and first['reader_b']['level'] == '1' and 'adjudicated' in first['basis']
    assert final['https://aws.amazon.com/about-aws/whats-new/2010/01/r01/']['adjudication'] is None


@check
def a_chunk_with_no_valid_reply_stops_and_keeps_its_attempts():
    from early_label import label
    with tempfile.TemporaryDirectory() as tmp:
        try:
            label(label_records(2), Path(tmp), CannedClient(lambda role, records, call: 'not json'))
            raise AssertionError('three invalid replies must stop the run')
        except RuntimeError:
            pass
        failed = json.loads((Path(tmp) / 'reader_a/chunk000.failed.json').read_text())
        assert len(failed['attempts']) == 3 and not (Path(tmp) / 'final.json').exists()


@check
def the_prompt_is_the_data_guide_rubric_plus_the_hindsight_instruction():
    from early_label import prompts, HINDSIGHT
    guide = (Path(__file__).resolve().parent.parent / 'DATA_GUIDE.md').read_text()
    section = guide.split('## Magnitude categories\n', 1)[1].split('\n## ', 1)[0].strip()
    for prompt in prompts().values():
        assert section in prompt and HINDSIGHT in prompt
        assert '| `4` | Major product expansion |' in prompt


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
