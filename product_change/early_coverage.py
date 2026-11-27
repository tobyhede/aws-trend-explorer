"""Measure 2010–2020 coverage against archived yearly index pages in the Internet Archive.

fetch   network: for each year, saves the Wayback CDX listing of captures of that year's index page, then
        saves captures in order of preference until one holds announcement links. A rerun skips saved files.
report  offline: compares each year's chosen capture with the snapshot inventory and writes coverage.json and
        coverage.txt. It reports a measured gap and adds nothing to the corpus.

A capture is chosen from status-200 captures between 1 December of the year and 31 March of the next: the
earliest on or after 1 January of the next year, otherwise the latest before it. A capture before year end
cannot list later posts, so those years state the capture date. A year with no usable capture is unchecked.
"""
import argparse
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date
from html.parser import HTMLParser

from early_collect import SNAPSHOT, SITE, YEARS, parse

USER_AGENT = 'aws-trend-explorer-coverage/1.0'
DELAY_SECONDS = 3
CDX = 'https://web.archive.org/cdx/search/cdx'
INDEX = 'aws.amazon.com/about-aws/whats-new/{year}/'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_manifest(root):
    path = root / 'archive/manifest.json'
    return json.loads(path.read_text()) if path.exists() else {'source': 'Internet Archive Wayback Machine', 'files': []}


def save_file(root, name, data, url, retrieved):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    manifest = read_manifest(root)
    manifest['files'] = sorted([f for f in manifest['files'] if f['file'] != name] + [
        {'file': name, 'url': url, 'retrieved': retrieved, 'bytes': len(data), 'sha256': digest(data)}], key=lambda f: f['file'])
    (root / 'archive/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def cdx_url(year):
    query = {'url': INDEX.format(year=year), 'from': f'{year}1201', 'to': f'{year + 1}0331',
             'filter': 'statuscode:200', 'output': 'json', 'fl': 'timestamp,original,statuscode,length,digest'}
    return CDX + '?' + urllib.parse.urlencode(query)


def capture_url(timestamp, original):
    return f'https://web.archive.org/web/{timestamp}id_/{original}'


def candidates(cdx_rows, year):
    """Captures in order of preference."""
    rows = [dict(zip(cdx_rows[0], row)) for row in cdx_rows[1:]] if cdx_rows else []
    rows = [r for r in rows if r['statuscode'] == '200']
    boundary = f'{year + 1}0101'
    after = sorted((r for r in rows if r['timestamp'] >= boundary), key=lambda r: r['timestamp'])
    before = sorted((r for r in rows if r['timestamp'] < boundary), key=lambda r: r['timestamp'], reverse=True)
    return after + before


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.extend(value for name, value in attrs if name == 'href' and value)


def announcement_paths(page, year):
    """Paths of the year's announcement links, without query or fragment, each ending in a slash."""
    parser = _Links()
    parser.feed(page.decode('utf-8', 'replace'))
    pattern = re.compile(rf'^/about-aws/whats-new/{year}/\d\d/.+')
    paths = {}
    for href in parser.hrefs:
        path = urllib.parse.urlsplit(urllib.parse.urljoin(SITE + '/', href)).path
        if pattern.match(path):
            path = path if path.endswith('/') else path + '/'
            paths.setdefault(path.lower(), path)
    return paths


def page_name(year, timestamp):
    return f'archive/pages/{year}_{timestamp}.html'


def fetch_url(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except OSError:
            if attempt == 3:
                raise
            time.sleep(DELAY_SECONDS * 2 ** (attempt + 1))


def fetch(root=SNAPSHOT, years=YEARS, fetch_url=fetch_url, delay=DELAY_SECONDS):
    today = date.today().isoformat()

    def saved(name, url):
        if not (root / name).exists():
            save_file(root, name, fetch_url(url), url, today)
            print('saved', name)
            time.sleep(delay)
        return (root / name).read_bytes()

    for year in years:
        rows = json.loads(saved(f'archive/cdx/{year}.json', cdx_url(year)) or b'[]')
        for capture in candidates(rows, year):
            if announcement_paths(saved(page_name(year, capture['timestamp']), capture_url(capture['timestamp'], capture['original'])), year):
                break


def report(root=SNAPSHOT, years=YEARS, write=False):
    manifest = read_manifest(root)
    for entry in manifest['files']:
        assert digest((root / entry['file']).read_bytes()) == entry['sha256'], f'{entry["file"]} changed since retrieval'
    records = parse(root)
    result = {'method': __doc__.split('\n\n', 2)[2].strip(), 'years': []}
    for year in years:
        inventory = [r for r in records if r['announcement_date'][:4] == str(year)]
        known = {urllib.parse.urlsplit(r['source_url']).path.lower() for r in inventory}
        row = {'year': year, 'status': 'unchecked', 'capture': None, 'capture_date': None, 'capture_url': None,
               'archived_links': None, 'inventory': len(inventory), 'inventory_through_capture': None,
               'absent_count': None, 'absent': []}
        cdx_file = root / f'archive/cdx/{year}.json'
        rows = json.loads(cdx_file.read_bytes() or b'[]') if cdx_file.exists() else []
        for capture in candidates(rows, year):
            name = page_name(year, capture['timestamp'])
            if not (root / name).exists():
                continue
            links = announcement_paths((root / name).read_bytes(), year)
            if not links:
                continue
            stamp = capture['timestamp']
            captured = f'{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}'
            absent = sorted(SITE + path for key, path in links.items() if key not in known)
            row.update(status='checked', capture=stamp, capture_date=captured, file=name,
                       capture_url=capture_url(stamp, capture['original']), archived_links=len(links),
                       inventory_through_capture=sum(r['announcement_date'] <= captured for r in inventory),
                       absent_count=len(absent), absent=absent)
            break
        result['years'].append(row)
    if write:
        (root / 'coverage.json').write_text(json.dumps(result, indent=2) + '\n')
        lines = ['Coverage of the 2010–2020 snapshot against archived yearly index pages', '',
                 'Absent means an announcement link on the archived page that the AWS directory API did not list on the collection date.',
                 'Missing posts are reported, not added. Link paths are compared without case, query or fragment.', '',
                 f'{"Year":<6}{"Capture":<13}{"Archived links":>16}{"Inventory":>11}{"Through capture":>17}{"Absent":>8}']
        for row in result['years']:
            if row['status'] == 'checked':
                lines.append(f'{row["year"]:<6}{row["capture_date"]:<13}{row["archived_links"]:>16}{row["inventory"]:>11}{row["inventory_through_capture"]:>17}{row["absent_count"]:>8}')
            else:
                lines.append(f'{row["year"]:<6}{"unchecked":<13}{"":>16}{row["inventory"]:>11}{"":>17}{"":>8}')
        (root / 'coverage.txt').write_text('\n'.join(lines) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=['fetch', 'report'])
    args = parser.parse_args()
    if args.action == 'fetch':
        fetch()
    result = report(write=True)
    print((SNAPSHOT / 'coverage.txt').read_text())
