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
def a_re_ask_says_why_the_previous_reply_was_rejected():
    from early_label import label
    copied = 'now lets customers choose option number 0 for every widget'
    client = CannedClient(lambda role, records, call: reply(records, reason=copied) if call == 1 else reply(records))
    with tempfile.TemporaryDirectory() as tmp:
        label(label_records(1), Path(tmp), client)
        attempts = json.loads((Path(tmp) / 'reader_a/chunk000.json').read_text())['attempts']
    first, second = client.calls[0]['system'], client.calls[1]['system']
    assert 'rejected' not in first and 'rejected' in second and 'choose option number for every widget' in second, second[-300:]
    assert attempts[1]['retry_note'] and second.endswith(attempts[1]['retry_note'])
    assert client.calls[2]['system'] == first  # reader B starts clean


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


@check
def the_claude_code_client_runs_a_fresh_toolless_session_on_the_subscription():
    import os
    from early_label import ClaudeCodeClient, SCHEMA
    seen = {}

    def run(command, **kwargs):
        seen.update(command=command, **kwargs)
        output = {'subtype': 'success', 'is_error': False, 'session_id': 'abc', 'result': '{"ratings": []}',
                  'structured_output': {'ratings': []},
                  'modelUsage': {'claude-haiku-5-5': {'inputTokens': 9, 'outputTokens': 2},
                                 'claude-fable-5-2': {'inputTokens': 2, 'outputTokens': 50}}}
        return type('Done', (), {'returncode': 0, 'stdout': json.dumps(output), 'stderr': ''})()

    os.environ['ANTHROPIC_API_KEY'] = 'should-not-be-passed'
    try:
        response = ClaudeCodeClient(run=run).complete('claude-fable-5-2', 'SYSTEM', '[{"index": 0}]')
    finally:
        del os.environ['ANTHROPIC_API_KEY']
    command = seen['command']
    assert command[:2] == ['claude', '-p'] and seen['input'] == '[{"index": 0}]'
    for flag, value in [('--model', 'claude-fable-5-2'), ('--system-prompt', 'SYSTEM'), ('--tools', ''), ('--setting-sources', ''),
                        ('--output-format', 'json'), ('--json-schema', json.dumps(SCHEMA))]:
        assert command[command.index(flag) + 1] == value, flag
    assert '--no-session-persistence' in command and '--strict-mcp-config' in command
    assert 'ANTHROPIC_API_KEY' not in seen['env'] and seen['cwd'] != str(Path.cwd())
    assert json.loads(response['text']) == {'ratings': []} and response['model'] == 'claude-fable-5-2'
    assert response['request_id'] == 'abc'


def by_index_policy(role, records, call):
    """Deterministic whatever the call order: readers disagree on even indices, the adjudicator says 3."""
    if role == 'adjudicator':
        return reply(records, level='3', reason='A distinct new operation appears in the service.')
    return json.dumps({'ratings': [{'index': r['index'], 'level': '2', 'reason': 'Adds an option to an existing operation.', 'confidence': 'high'}
                                   for r in records]})


@check
def concurrent_requests_give_the_same_labels_as_one_at_a_time():
    from early_label import label
    with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as many:
        serial = label(label_records(60), Path(one), CannedClient(by_index_policy))
        parallel = label(label_records(60), Path(many), CannedClient(by_index_policy), workers=4)
    assert serial == parallel and len(parallel) == 60


@check
def the_bridge_sample_reaches_readers_without_its_pass_or_any_recorded_label():
    from early_label import bridge
    sample = [{'index': i, 'pass': '2025-2026' if i < 2 else '2021-2024', 'date': '2025-01-0' + str(i + 1),
               'url': f'https://x/{i}', 'title': f'T{i}', 'text': f'Text {i}.'} for i in range(4)]
    client = CannedClient(lambda role, records, call: reply(records))
    with tempfile.TemporaryDirectory() as tmp:
        final = bridge(sample, Path(tmp), client)
    shown = [row for call in client.calls for row in json.loads(call['user'])]
    assert shown and all(set(row) == {'index', 'date', 'url', 'title', 'text'} for row in shown), shown[0]
    assert len(final) == 4 and all(r['reader_a'] and r['reader_b'] for r in final.values())


@check
def the_reference_reading_is_one_blind_opus_reading_per_hidden_record():
    from early_label import reference
    sample = [{'index': i, 'date': '2012-01-01', 'url': f'https://x/{i}', 'title': f'T{i}', 'text': f'Text {i}.'} for i in range(30)]
    client = CannedClient(lambda role, records, call: reply(records, level='1'))
    with tempfile.TemporaryDirectory() as tmp:
        result = reference(sample, Path(tmp), client)
    assert {c['model'] for c in client.calls} == {'claude-opus-5-5'} and len(client.calls) == 2
    assert all(c['role'] == 'reader' and 'reader_a' not in c['user'] for c in client.calls)
    assert len(result) == 30 and {r['level'] for r in result.values()} == {'1'} and result['https://x/0']['model'] == 'claude-opus-5-5'


@check
def weighted_agreement_matches_a_hand_worked_example():
    from early_score import weighted_agreement
    # A: N=100, n=10, 5 agree; B: N=900, n=10, 9 agree. Weighted 0.1*0.5 + 0.9*0.9 = 0.86 (unweighted 14/20 = 0.70).
    # Variance with finite-population correction: 0.1²·0.25/10·0.9 + 0.9²·0.09/10·(890/900) = 0.000225 + 0.0072090 = 0.0074340,
    # so the standard error is 0.086221 and the 95% interval 0.86 ± 0.16899 = 0.6910 to 1.0290, capped at 1.
    p, (low, high) = weighted_agreement({'A': (100, 10, 5), 'B': (900, 10, 9)})
    assert abs(p - 0.86) < 1e-9, p
    assert abs(low - 0.69101) < 1e-4 and high == 1.0, (low, high)


@check
def audit_scores_agreement_per_year_per_level_and_weighted():
    from early_score import audit
    sample = [{'index': i, 'date': f'{y}-03-01', 'url': f'u{y}{i}'} for i, y in enumerate([2010] * 2 + [2011] * 2)]
    final = {'u20100': {'level': '3'}, 'u20101': {'level': '2'}, 'u20112': {'level': '1'}, 'u20113': {'level': 'NA'}}
    reference = {'u20100': {'level': '3'}, 'u20101': {'level': '3'}, 'u20112': {'level': '1'}, 'u20113': {'level': 'NA'}}
    metrics = audit(sample, reference, final, {'2010': 10, '2011': 30})
    assert metrics['by_year']['2010']['exact'] == 1 and metrics['by_year']['2011']['exact'] == 2
    assert metrics['exact_agreement'] == 3 and metrics['sample_size'] == 4
    assert abs(metrics['weighted_agreement'] - (0.25 * 0.5 + 0.75 * 1.0)) < 1e-9
    level3 = metrics['by_level']['3']
    assert (level3['correct'], level3['predicted'], level3['reference']) == (1, 1, 2)
    assert metrics['confusion'] == {'1 -> 1': 1, '2 -> 3': 1, '3 -> 3': 1, 'NA -> NA': 1}
    assert 'agreement between AI readings' in metrics['interpretation']


@check
def bridge_scores_a_confusion_table_with_intervals_per_pass_and_combined():
    from early_score import bridge_scores
    sample = [{'index': i, 'pass': p, 'url': f'u{i}'} for i, p in enumerate(['2025-2026'] * 3 + ['2021-2024'] * 2)]
    recorded = {'u0': '2', 'u1': '3', 'u2': 'NA', 'u3': '2', 'u4': 'U'}
    new = {'u0': {'level': '3'}, 'u1': {'level': '3'}, 'u2': {'level': 'NA'}, 'u3': {'level': '2'}, 'u4': {'level': '2'}}
    scores = bridge_scores(sample, new, recorded)
    recent, older, combined = scores['2025-2026'], scores['2021-2024'], scores['combined']
    assert (recent['n'], recent['exact'], older['n'], older['exact'], combined['n'], combined['exact']) == (3, 2, 2, 1, 5, 3)
    assert recent['confusion'] == {'2 -> 3': 1, '3 -> 3': 1, 'NA -> NA': 1}
    assert combined['confusion'] == {'2 -> 2': 1, '2 -> 3': 1, '3 -> 3': 1, 'NA -> NA': 1, 'U -> 2': 1}
    low, high = combined['wilson_95']
    assert low < 0.6 < high
    assert combined['levels']['2'] == {'recorded': 2, 'new': 2, 'recorded_wilson_95': combined['levels']['2']['recorded_wilson_95'],
                                       'new_wilson_95': combined['levels']['2']['new_wilson_95']}
    assert combined['levels']['U']['recorded'] == 1 and combined['levels']['U']['new'] == 0
    assert combined['two_to_three'] == 1 and combined['three_to_two'] == 0


@check
def period_tables_match_a_hand_built_corpus():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'substantive_trends'))
    from periods import tables
    rows = []
    # 2018: 4 matched records (levels 3, 2, 1, NA) plus one on 29 October that the matched period drops.
    rows += [('2018-02-01', '3'), ('2018-03-01', '2'), ('2018-04-01', '1'), ('2018-10-28', 'NA'), ('2018-10-29', '5')]
    # 2019: 6 matched (3, 3, 2, 2, U, NA). 2020: 3 (4, 2, 1). 2022: 2 (5, NA). 2023: 4 (3, 2, 2, 1).
    rows += [('2019-01-01', '3'), ('2019-01-02', '3'), ('2019-01-03', '2'), ('2019-01-04', '2'), ('2019-01-05', 'U'), ('2019-01-06', 'NA')]
    rows += [('2020-05-01', '4'), ('2020-05-02', '2'), ('2020-05-03', '1')]
    rows += [('2022-01-01', '5'), ('2022-01-02', 'NA')]
    rows += [('2023-01-01', '3'), ('2023-01-02', '2'), ('2023-01-03', '2'), ('2023-01-04', '1')]
    result = tables(rows, periods={'pre-COVID': (2018, 2019), 'COVID': (2020, 2021), 'post-COVID': (2022, 2023)}, sensitivity=(2019, 2019))
    annual = {r['year']: (r['announcements'], r['strict'], r['broad']) for r in result['annual']}
    assert annual == {2018: (4, 1, 2), 2019: (6, 2, 4), 2020: (3, 1, 2), 2021: (0, 0, 0), 2022: (2, 1, 1), 2023: (4, 1, 3)}, annual
    changes = {r['period']: r for r in result['median_change']}
    # Changes ending in each period's years: pre-COVID 2019 vs 2018 only (2018 has no earlier year): +50%, +100%, +100%.
    assert changes['pre-COVID']['announcements'] == 50.0 and changes['pre-COVID']['strict'] == 100.0 and changes['pre-COVID']['years'] == [2019]
    # COVID: 2020 vs 2019 = -50% (announcements); 2021 vs 2020 = -100%; median -75%.
    assert changes['COVID']['announcements'] == -75.0, changes['COVID']
    # post-COVID: 2022 vs 2021 has a zero base and is left out; 2023 vs 2022 = +100%.
    assert changes['post-COVID']['announcements'] == 100.0 and changes['post-COVID']['years'] == [2023], changes['post-COVID']
    assert changes['2019–2019']['announcements'] == 50.0
    shares = {(r['period'], r['level']): r for r in result['shares']}
    assert [r['level'] for r in result['shares'] if r['period'] == 'pre-COVID'] == ['1', '2', '3', '4', '5', 'U', 'NA']
    assert shares[('pre-COVID', '3')]['count'] == 3 and shares[('pre-COVID', '3')]['total'] == 10
    assert shares[('pre-COVID', 'U')]['count'] == 1 and shares[('pre-COVID', 'NA')]['count'] == 2
    assert shares[('pre-COVID', '5')]['count'] == 0  # the 29 October record is outside the matched period
    low, high = shares[('pre-COVID', '3')]['wilson_95']
    assert low < 0.3 < high


@check
def the_interpretation_may_use_only_numbers_from_the_tables():
    from periods import check_report
    tables_text = 'Level 3: pre-COVID 17.4% (16.4–18.6%); post-COVID 12.5%; 2010 48; +45.1%'
    check_report('Level 3 was 17.4% before and 12.5% after; 2010 had 48 records; growth +45.1%.', tables_text)
    try:
        check_report('Level 3 fell by 4.9 points.', tables_text)
        raise AssertionError('a derived number must be refused')
    except AssertionError as error:
        assert '4.9' in str(error), error


def final_labels(levels):
    return {f'https://aws.amazon.com/about-aws/whats-new/2015/01/r{i:03d}/': {
        'index': i, 'date': '2015-01-01', 'title': f'T{i}', 'text': f'Text {i}.', 'level': level, 'reason': f'Reason {i}.',
        'confidence': 'high', 'basis': 'early_review: two claude-fable-5-2 readers agreed'}
        for i, level in enumerate(levels)}


@check
def the_human_check_draws_forty_level_four_and_five_records_by_seed():
    from early_human import draw
    final = final_labels(['4', '5', '3', '2', 'NA'] * 20)
    sample = draw(final, 'seed-a', size=10)
    assert len(sample) == 10 and {r['level'] for r in sample} <= {'4', '5'}
    assert draw(final, 'seed-a', size=10) == sample and draw(final, 'seed-b', size=10) != sample
    assert set(sample[0]) >= {'url', 'title', 'text', 'level', 'reason'}


@check
def human_readings_are_counted_apart_and_must_be_complete():
    from early_human import score_readings
    sample = [{'url': f'u{i}', 'level': '4'} for i in range(3)]
    result = score_readings(sample, {'u0': ('agree', ''), 'u1': ('disagree', 'reads as a level 3 addition'), 'u2': ('agree', '')})
    assert (result['agree'], result['disagree'], result['read']) == (2, 1, 3) and result['disagreements'][0]['note']
    assert 'maintainer' in result['interpretation'] and 'separate' in result['interpretation']
    for readings in [{'u0': ('agree', '')}, {'u0': ('yes', ''), 'u1': ('agree', ''), 'u2': ('agree', '')}]:
        try:
            score_readings(sample, readings)
            raise AssertionError('incomplete or invalid readings must be refused')
        except ValueError:
            pass


@check
def a_correction_replaces_the_label_and_keeps_the_original_in_the_basis():
    from early_label import apply_corrections
    early = {'https://aws.amazon.com/about-aws/whats-new/2015/01/a/': ('5', 'A new offering.', 'early_review: two claude-fable-5-2 readers agreed'),
             'https://aws.amazon.com/about-aws/whats-new/2015/01/b/': ('4', 'A new model.', 'early_review: two claude-fable-5-2 readers agreed')}
    corrected = apply_corrections(early, {'2015/01/a/': ('3', 'Adds an operation to an existing service.'), '2025/01/other/': ('1', 'x')})
    a = corrected['https://aws.amazon.com/about-aws/whats-new/2015/01/a/']
    assert a[:2] == ('3', 'Adds an operation to an existing service.') and 'correction' in a[2] and 'original level 5' in a[2], a
    assert corrected['https://aws.amazon.com/about-aws/whats-new/2015/01/b/'] == early['https://aws.amazon.com/about-aws/whats-new/2015/01/b/']


def main():
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
