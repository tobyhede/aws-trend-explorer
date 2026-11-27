"""Collect, freeze and parse the 2010–2020 AWS directory snapshot.

collect  pages the AWS directory API by year and saves each raw response unmodified, with a SHA-256 manifest.
         A rerun skips pages already saved. This is the only action that uses the network.
parse    reads only the saved responses and yields records with the corpus fields (used by later steps).
         A record a year tag lists but dated in another year is set aside and reported, not parsed.
check    offline: manifest hashes match and each year's parsed and set-aside records equal the count the API listed.

The 2021–2026 corpus is not collected again. Nothing is labelled and announcements.duckdb is not changed.
"""
import argparse
import hashlib
import html
import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / 'early_snapshot'
YEARS = range(2010, 2021)
API = 'https://aws.amazon.com/api/dirs/items/search'
SITE = 'https://aws.amazon.com'
PAGE_SIZE = 2000  # the largest size the API answers; smaller pages risk ties across page boundaries
USER_AGENT = 'aws-trend-explorer-collector/1.0'
DELAY_SECONDS = 3
COLUMNS = ['announcement_date', 'title', 'service', 'source_url', 'announcement_text', 'source_id', 'source_snapshot',
           'record_origin', 'release_type', 'enhancement_facets', 'review_basis', 'text_basis', 'text_source_url',
           'legacy_category', 'classification_cohort', 'facet_update', 'primary_scope', 'scope_basis', 'title_stage',
           'magnitude', 'affected_workload', 'magnitude_reason', 'magnitude_review', 'product_change_level',
           'product_change_reason', 'product_change_basis']
COHORT = 'pre-2021 extension'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def page_name(year, page):
    return f'raw/{year}_p{page:04d}.json'


def page_url(year, page):
    query = {'item.directoryId': 'whats-new-v2', 'sort_by': 'item.additionalFields.postDateTime', 'sort_order': 'asc',
             'size': PAGE_SIZE, 'item.locale': 'en_US', 'tags.id': f'whats-new-v2#year#{year}', 'page': page}
    return API + '?' + urllib.parse.urlencode(query)


def read_manifest(root):
    path = root / 'manifest.json'
    return json.loads(path.read_text()) if path.exists() else {'source': API, 'page_size': PAGE_SIZE, 'pages': []}


def save_page(root, year, page, data, url, collected):
    """Write one raw response byte for byte and record it in the manifest."""
    name = page_name(year, page)
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    manifest = read_manifest(root)
    manifest['pages'] = [p for p in manifest['pages'] if p['file'] != name] + [
        {'file': name, 'year': year, 'page': page, 'url': url, 'collected': collected, 'bytes': len(data), 'sha256': digest(data)}]
    manifest['pages'].sort(key=lambda p: p['file'])
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except OSError:
            if attempt == 3:
                raise
            time.sleep(DELAY_SECONDS * 2 ** (attempt + 1))


def collect(root=SNAPSHOT, years=YEARS, fetch=fetch, delay=DELAY_SECONDS):
    today = date.today().isoformat()
    for year in years:
        page = 0
        while True:
            path = root / page_name(year, page)
            if path.exists():
                data = path.read_bytes()
            else:
                url = page_url(year, page)
                data = fetch(url)
                json.loads(data)  # refuse to save something that is not JSON
                save_page(root, year, page, data, url, today)
                print('saved', page_name(year, page))
                time.sleep(delay)
            response = json.loads(data)
            if (page + 1) * PAGE_SIZE >= response['metadata']['totalHits']:
                break
            page += 1
    check(root)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs=None):
        self.parts.append(' ')

    handle_endtag = handle_startendtag = handle_starttag

    def handle_data(self, data):
        self.parts.append(data)


def plain(fragment):
    """Announcement HTML to the corpus's text form: each tag becomes a space, entities decode (except inside
    style and script, as the earlier collection left them), whitespace collapses."""
    parser = _Text()
    parser.feed(fragment or '')
    parser.close()
    return ' '.join(''.join(parser.parts).split())


def to_record(entry, snapshot_file):
    item, fields = entry['item'], entry['item']['additionalFields']
    url = SITE + fields['headlineUrl']
    products = [t['id'].split('#', 2)[2] for t in entry.get('tags', []) if t['id'].startswith('whats-new-v2#general-products#')]
    text = ' '.join(part for part in (plain(fields.get('postSummary')), plain(fields.get('postBody'))) if part)
    record = dict.fromkeys(COLUMNS)
    record.update({
        'announcement_date': fields['postDateTime'][:10], 'title': ' '.join(html.unescape(fields['headline']).split()),
        'service': '; '.join(sorted(products)) or 'unknown', 'source_url': url, 'announcement_text': text,
        'source_id': item['id'], 'source_snapshot': snapshot_file, 'record_origin': 'directory snapshot',
        'text_basis': 'AWS announcement text', 'text_source_url': url, 'classification_cohort': COHORT})
    return record


def listed_counts(root):
    """The totalHits the API reported on the first page of each year."""
    counts = {}
    for page in read_manifest(root)['pages']:
        if page['page'] == 0:
            counts[page['year']] = json.loads((root / page['file']).read_bytes())['metadata']['totalHits']
    return counts


def _entries(root):
    seen = set()
    for page in read_manifest(root)['pages']:
        for entry in json.loads((root / page['file']).read_bytes())['items']:
            record = to_record(entry, page['file'])
            if record['source_url'] in seen:
                raise ValueError(f'{record["source_url"]} listed twice in the snapshot')
            seen.add(record['source_url'])
            yield page['year'], record


def parse(root=SNAPSHOT):
    """Records dated in the year whose tag listed them, sorted by date and URL."""
    records = [r for year, r in _entries(root) if r['announcement_date'][:4] == str(year)]
    return sorted(records, key=lambda r: (r['announcement_date'], r['source_url']))


def misdated(root=SNAPSHOT):
    """Records a year tag listed although they are dated in another year. They are reported, not parsed."""
    return [{'year_tag': year, 'announcement_date': r['announcement_date'], 'source_url': r['source_url'], 'title': r['title']}
            for year, r in _entries(root) if r['announcement_date'][:4] != str(year)]


def check(root=SNAPSHOT):
    """Offline: hashes match the manifest, and parsed plus set-aside records equal what each year tag listed."""
    manifest = read_manifest(root)
    for page in manifest['pages']:
        assert digest((root / page['file']).read_bytes()) == page['sha256'], f'{page["file"]} changed since collection'
    saved = {p['file'] for p in manifest['pages']}
    on_disk = {str(p.relative_to(root)) for p in (root / 'raw').glob('*.json')}
    assert saved == on_disk, f'raw files not in the manifest: {sorted(on_disk - saved)}; missing: {sorted(saved - on_disk)}'
    listed = listed_counts(root)
    parsed = Counter(int(r['announcement_date'][:4]) for r in parse(root))
    aside = Counter(r['year_tag'] for r in misdated(root))
    accounted = {year: parsed[year] + aside[year] for year in set(parsed) | set(aside)}
    assert accounted == listed, f'parsed {dict(parsed)} and set aside {dict(aside)}, but the API listed {listed}'
    print('Snapshot verified:', ', '.join(f'{y} {parsed[y]}' for y in sorted(listed)), f'= {sum(parsed.values()):,} records;',
          f'{sum(aside.values())} listed under a year tag but dated in another year, set aside')
    return listed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=['collect', 'check'])
    args = parser.parse_args()
    {'collect': collect, 'check': check}[args.action]()
