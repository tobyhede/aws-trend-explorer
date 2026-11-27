"""Label the 2010–2020 records through the Claude API: two independent readers, a third reading on disagreement.

label TARGET     calls the model through headless Claude Code on the Claude subscription (or, with --client api,
                 the Claude API with a key and product_change/labelling-requirements.txt). Every chunk
                 of about 25 records goes to each reader in a fresh request; neither reader sees the other.
                 A reply missing a record, holding a level outside 1–5, U and NA, or copying the announcement
                 text into a reason is rejected and asked again. A rerun skips chunks already saved.
check TARGET     offline: replays the saved readings and adjudications and confirms final.json.

TARGET is a year (2010–2020), bridge (the bridge sample under the full protocol, blind to recorded labels) or
reference (one blind reading of the hidden sample by claude-opus-5-5, the audit reference).

This is a step of its own, not part of the rebuild. The build replays final.json and never calls a model.
Every request and reply is saved under early_review/labels/<year>/ with the model ID and the prompt.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from early_collect import YEARS, parse

HERE = Path(__file__).resolve().parent
LABELS = HERE / 'early_review' / 'labels'
BRIDGE = HERE / 'early_review' / 'bridge'
REFERENCE = HERE / 'early_review' / 'reference'
READER_MODEL = ADJUDICATOR_MODEL = 'claude-fable-5-2'
REFERENCE_MODEL = 'claude-opus-5-5'
REVIEW = HERE / 'early_review'
CHUNK_SIZE = 25
ATTEMPTS = 3
LEVELS = ['1', '2', '3', '4', '5', 'U', 'NA']
CONFIDENCE = ['high', 'medium', 'low']
SHINGLE = 8  # the same copied-run length hosted/check_site.py uses
HINDSIGHT = ('Rate only the change the text describes at the time it was published. Do not use what you know about '
             'what the product, feature or service later became, or about later announcements.')
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['ratings'], 'properties': {'ratings': {
    'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'required': ['index', 'level', 'reason', 'confidence'],
                               'properties': {'index': {'type': 'integer'}, 'level': {'type': 'string', 'enum': LEVELS},
                                              'reason': {'type': 'string'}, 'confidence': {'type': 'string', 'enum': CONFIDENCE}}}}}}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def rubric():
    """The Magnitude categories section of DATA_GUIDE.md, verbatim."""
    guide = (HERE.parent / 'DATA_GUIDE.md').read_text()
    return guide.split('## Magnitude categories\n', 1)[1].split('\n## ', 1)[0].strip()


def prompts():
    common = (f'{rubric()}\n\n{HINDSIGHT}\n\n'
              'Each reason is one line in your own words. Do not copy phrases from the announcement text. '
              'Confidence is high, medium or low. Return one rating for every record, keyed by its index.')
    reader = ('You rate AWS "What\'s New" announcements on the product-change scale below. The user message is a JSON list '
              'of records with index, date, URL, title and text.\n\n' + common)
    adjudicator = ('You adjudicate AWS "What\'s New" announcements on the product-change scale below. Two independent readers '
                   'rated each record differently. Each record in the user message has its index, date, URL, title and text, '
                   'and both readers\' level, reason and confidence. Read the text and give the final rating; it may differ '
                   'from both readers.\n\n' + common)
    return {'reader': reader, 'adjudicator': adjudicator}


def words(text):
    return re.findall(r'[a-z]+', text.lower())


def shingles(text):
    tokens = words(text)
    return {' '.join(tokens[i:i + SHINGLE]) for i in range(len(tokens) - SHINGLE + 1)}


def validate(text, records):
    """Ratings keyed by index, or a ValueError saying why the reply is rejected."""
    try:
        ratings = json.loads(text)['ratings']
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError(f'not the requested JSON: {error}')
    expected = {r['index']: r for r in records}
    result = {}
    for rating in ratings:
        index = rating.get('index') if isinstance(rating, dict) else None
        if index not in expected or index in result:
            raise ValueError(f'unexpected or repeated index {index!r}')
        level, reason, confidence = rating.get('level'), rating.get('reason'), rating.get('confidence')
        if level not in LEVELS:
            raise ValueError(f'index {index}: level {level!r} is outside 1–5, U and NA')
        if confidence not in CONFIDENCE:
            raise ValueError(f'index {index}: confidence {confidence!r}')
        if not isinstance(reason, str) or not reason.strip() or '\n' in reason.strip():
            raise ValueError(f'index {index}: the reason must be one non-empty line')
        record = expected[index]
        if shingles(reason) & (shingles(record['text']) - shingles(record['title'])):
            raise ValueError(f'index {index}: the reason copies the announcement text')
        result[index] = {'level': level, 'reason': reason.strip(), 'confidence': confidence}
    missing = sorted(set(expected) - set(result))
    if missing:
        raise ValueError(f'missing indices {missing}')
    return result


def ask(client, model, system, records, path):
    """One chunk: fresh requests until a reply validates. Saves every attempt; skips a chunk already saved."""
    if path.exists():
        saved = json.loads(path.read_text())
        assert saved['indices'] == [r['index'] for r in records], f'{path} holds other records'
        return {int(k): v for k, v in saved['ratings'].items()}
    user = json.dumps(records, ensure_ascii=False, indent=1)
    attempts = []
    for _ in range(ATTEMPTS):
        response = client.complete(model, system, user)
        attempt = {'model': response.get('model'), 'stop_reason': response.get('stop_reason'), 'request_id': response.get('request_id'),
                   'usage': response.get('usage'), 'reply': response.get('text', ''), 'rejected': None}
        attempts.append(attempt)
        try:
            ratings = validate(attempt['reply'], records)
        except ValueError as error:
            attempt['rejected'] = str(error)
            continue
        if attempt['model'] != model:
            attempt['rejected'] = f'served by {attempt["model"]}, not {model}'
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'model': model, 'system_sha256': digest(system), 'indices': [r['index'] for r in records],
                                    'user': user, 'attempts': attempts, 'ratings': ratings}, indent=1, ensure_ascii=False) + '\n')
        return ratings
    failed = path.with_suffix('.failed.json')
    failed.parent.mkdir(parents=True, exist_ok=True)
    failed.write_text(json.dumps({'model': model, 'system_sha256': digest(system), 'user': user, 'attempts': attempts}, indent=1, ensure_ascii=False) + '\n')
    raise RuntimeError(f'{path.name}: no valid reply in {ATTEMPTS} attempts; see {failed}')


def chunks(rows):
    return [rows[i:i + CHUNK_SIZE] for i in range(0, len(rows), CHUNK_SIZE)]


def freeze(root, name, value):
    """Write a value once; later runs must find the same value."""
    path = root / name
    if path.exists():
        assert json.loads(path.read_text()) == value, f'{path} differs from this run; the evidence is frozen'
    else:
        root.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + '\n')


def ask_all(client, jobs, workers):
    """Run (model, system, chunk, path) jobs, up to workers at once; results in job order. A failed chunk stops the
    run after the others finish, so their evidence is kept."""
    if workers <= 1:
        return [ask(client, *job) for job in jobs]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(ask, client, *job) for job in jobs]
        errors = [f.exception() for f in futures if f.exception()]
    if errors:
        raise errors[0]
    return [f.result() for f in futures]


def freeze_prompts(root, system):
    freeze(root, 'prompts.json', {'reader_model': READER_MODEL, 'adjudicator_model': ADJUDICATOR_MODEL, 'hindsight_instruction': HINDSIGHT,
                                  'reader': system['reader'], 'reader_sha256': digest(system['reader']),
                                  'adjudicator': system['adjudicator'], 'adjudicator_sha256': digest(system['adjudicator'])})


def two_readers(inputs, root, client, workers=1, write=True):
    """The protocol on prepared reader inputs: two readers, a third reading on disagreement; returns final ratings by URL."""
    system = prompts()
    freeze(root, 'inputs.json', inputs)
    freeze_prompts(root, system)
    jobs = [(READER_MODEL, system['reader'], chunk, root / reader / f'chunk{n:03d}.json')
            for reader in ('reader_a', 'reader_b') for n, chunk in enumerate(chunks(inputs))]
    results = ask_all(client, jobs, workers)
    half = len(results) // 2
    a = {i: r for part in results[:half] for i, r in part.items()}
    b = {i: r for part in results[half:] for i, r in part.items()}
    disputed = [dict(row, reader_a=a[row['index']], reader_b=b[row['index']]) for row in inputs if a[row['index']]['level'] != b[row['index']]['level']]
    jobs = [(ADJUDICATOR_MODEL, system['adjudicator'], chunk, root / 'adjudication' / f'chunk{n:03d}.json') for n, chunk in enumerate(chunks(disputed))]
    adjudicated = {i: r for part in ask_all(client, jobs, workers) for i, r in part.items()}
    final = {}
    for row in inputs:
        i = row['index']
        if i in adjudicated:
            decision, basis = adjudicated[i], f'early_review: readers disagreed; adjudicated by {ADJUDICATOR_MODEL}'
        else:
            decision, basis = a[i], f'early_review: two {READER_MODEL} readers agreed'
        final[row['url']] = {'index': i, **decision, 'basis': basis, 'reader_a': a[i], 'reader_b': b[i], 'adjudication': adjudicated.get(i)}
    if write:
        (root / 'final.json').write_text(json.dumps(final, indent=1, ensure_ascii=False) + '\n')
    return final


def label(records, root, client, write=True, workers=1):
    """Label corpus records; returns final ratings keyed by source URL and, unless write is False, writes final.json."""
    ordered = sorted(records, key=lambda r: (r['announcement_date'], r['source_url']))
    inputs = [{'index': i, 'date': r['announcement_date'], 'url': r['source_url'], 'title': r['title'], 'text': r['announcement_text']}
              for i, r in enumerate(ordered)]
    return two_readers(inputs, root, client, workers, write)


def reader_inputs(sample):
    """Reader inputs from a frozen sample: index, date, URL, title and text only (the bridge sample's pass is dropped)."""
    return [{k: row[k] for k in ('index', 'date', 'url', 'title', 'text')} for row in sample]


def bridge(sample, root, client, write=True, workers=1):
    """The bridge sample under the full protocol, blind to the recorded labels."""
    return two_readers(reader_inputs(sample), root, client, workers, write)


def reference(sample, root, client, write=True, workers=1):
    """One blind reading of the hidden sample by the reference model; it sees the text only, never a reader's rating."""
    system = prompts()['reader']
    inputs = reader_inputs(sample)
    freeze(root, 'inputs.json', inputs)
    freeze(root, 'prompts.json', {'reference_model': REFERENCE_MODEL, 'hindsight_instruction': HINDSIGHT, 'reader': system, 'reader_sha256': digest(system)})
    jobs = [(REFERENCE_MODEL, system, chunk, root / 'reference' / f'chunk{n:03d}.json') for n, chunk in enumerate(chunks(inputs))]
    ratings = {i: r for part in ask_all(client, jobs, workers) for i, r in part.items()}
    result = {row['url']: {'index': row['index'], **ratings[row['index']], 'model': REFERENCE_MODEL} for row in inputs}
    if write:
        (root / 'reference.json').write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n')
    return result


class _NoNetwork:
    """A client that refuses every request, so check uses saved evidence only and fails on any unsaved chunk."""

    def complete(self, model, system, user):
        raise AssertionError('a chunk has no saved evidence')


def targets():
    """Each labelling target: its evidence folder and how to run it on a client."""
    found = {str(y): (LABELS / str(y), lambda client, write=True, workers=1, y=y: label(
        [r for r in parse() if r['announcement_date'].startswith(str(y))], LABELS / str(y), client, write, workers)) for y in YEARS}
    found['bridge'] = (BRIDGE, lambda client, write=True, workers=1: bridge(json.loads((REVIEW / 'bridge_sample.json').read_text()), BRIDGE, client, write, workers))
    found['reference'] = (REFERENCE, lambda client, write=True, workers=1: reference(json.loads((REVIEW / 'hidden_sample.json').read_text()), REFERENCE, client, write, workers))
    return found


def check(target):
    root, run = targets()[target]
    name = 'reference.json' if target == 'reference' else 'final.json'
    saved = json.loads((root / name).read_text())
    replayed = run(_NoNetwork(), write=False)
    assert replayed == saved, f'{name} does not match the saved readings'
    adjudicated = sum(r.get('adjudication') is not None for r in saved.values())
    print(f'{target}: {len(saved)} records replayed from saved evidence; {adjudicated} adjudicated; levels',
          dict(sorted(Counter(r['level'] for r in saved.values()).items())))


class ClaudeCodeClient:
    """The default client: a headless Claude Code session on the maintainer's Claude subscription.

    Each request is a fresh session with the reader's system prompt in place of Claude Code's own, no tools, no MCP
    servers, no settings, CLAUDE.md files or memory, run from an empty folder. API key variables are removed, so the
    session uses the subscription login rather than API billing. Claude Code attaches a short account note to the
    context; nothing else reaches the model.
    """

    def __init__(self, run=None, timeout=900):
        import subprocess
        self.run, self.timeout = run or subprocess.run, timeout

    def complete(self, model, system, user):
        import os
        import tempfile
        command = ['claude', '-p', '--model', model, '--effort', 'high', '--system-prompt', system, '--tools', '',
                   '--strict-mcp-config', '--setting-sources', '', '--disable-slash-commands', '--no-session-persistence',
                   '--output-format', 'json', '--json-schema', json.dumps(SCHEMA)]
        env = {k: v for k, v in os.environ.items() if k not in {'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN'}}
        with tempfile.TemporaryDirectory() as empty:
            done = self.run(command, input=user, capture_output=True, text=True, env=env, cwd=empty, timeout=self.timeout)
        try:
            output = json.loads(done.stdout)
        except ValueError:
            return {'text': '', 'model': None, 'stop_reason': f'claude exited {done.returncode}: {done.stderr[-500:]}'}
        usage = output.get('modelUsage') or {}
        answering = [m for m, u in usage.items() if u.get('outputTokens')]
        served = model if model in answering else max(answering, key=lambda m: usage[m]['outputTokens'], default=None)
        structured = output.get('structured_output')
        return {'text': json.dumps(structured) if structured is not None else (output.get('result') or ''),
                'model': served, 'stop_reason': output.get('subtype') if not output.get('is_error') else f'error: {output.get("result")}',
                'request_id': output.get('session_id'),
                'usage': {m: {'input_tokens': u.get('inputTokens'), 'cache_creation_input_tokens': u.get('cacheCreationInputTokens'),
                              'cache_read_input_tokens': u.get('cacheReadInputTokens'), 'output_tokens': u.get('outputTokens')} for m, u in usage.items()}}


class AnthropicClient:
    """Optional: the Claude API with an API key (labelling-requirements.txt)."""

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic()

    def complete(self, model, system, user):
        # No server-side fallbacks: a reading from another model would not be the protocol's reader. A refusal is a rejected attempt.
        response = self.client.messages.create(
            model=model, max_tokens=16000, system=system, messages=[{'role': 'user', 'content': user}],
            output_config={'effort': 'high', 'format': {'type': 'json_schema', 'schema': SCHEMA}})
        text = '' if response.stop_reason == 'refusal' else next((b.text for b in response.content if b.type == 'text'), '')
        return {'text': text, 'model': response.model, 'stop_reason': response.stop_reason, 'request_id': getattr(response, '_request_id', None),
                'usage': {'input_tokens': response.usage.input_tokens, 'output_tokens': response.usage.output_tokens}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=['label', 'check'])
    parser.add_argument('target', choices=[str(y) for y in YEARS] + ['bridge', 'reference'],
                        help='a year of 2010–2020 records, the bridge sample, or the hidden sample\'s reference reading')
    parser.add_argument('--client', choices=['claude-code', 'api'], default='claude-code',
                        help='claude-code (default) uses the Claude subscription through headless Claude Code; api needs an API key')
    parser.add_argument('--workers', type=int, default=1, help='requests in flight at once')
    args = parser.parse_args()
    if args.action == 'label':
        targets()[args.target][1](ClaudeCodeClient() if args.client == 'claude-code' else AnthropicClient(), workers=args.workers)
    check(args.target)
