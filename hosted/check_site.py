"""Check the hosted explorer's upload set before publishing. Run from the repository root:

    .venv/bin/python hosted/check_site.py

Everything under hosted/site/ is uploaded, so this fails if that directory holds an unexpected file,
saved announcement text, a request to another host, a stale supporting page or a broken link.
"""
import re
import sys
from html import unescape
from pathlib import Path
import duckdb

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = HERE / 'site'
sys.path[:0] = [str(HERE), str(ROOT / 'product_change')]
import pages
from public_dataset import FIELDS, NAME, PATH

ALLOWED_SUFFIXES = {'.html', '.js', '.css', '.parquet'}
ALLOWED_NAMES = {'_headers', 'LICENSE'}
SHINGLE = 8  # consecutive words; long enough that a match is copied text, not a shared phrase


def words(text):
    return re.findall(r'[a-z]+', text.lower())


def shingles(text):
    tokens = words(text)
    return {' '.join(tokens[i:i + SHINGLE]) for i in range(len(tokens) - SHINGLE + 1)}


def check():
    files = sorted(p for p in SITE.rglob('*') if p.is_file())
    unexpected = [str(p.relative_to(SITE)) for p in files if p.suffix not in ALLOWED_SUFFIXES and p.name not in ALLOWED_NAMES]
    assert not unexpected, f'Unexpected files in the upload set: {unexpected}'

    # Supporting pages are the current output of pages.py.
    for name, text in pages.render().items():
        assert (SITE / name).read_text() == text, f'{name} is stale: run hosted/pages.py'

    with duckdb.connect(str(ROOT / 'announcements.duckdb'), read_only=True) as db:
        # Every dated dataset has the nine public fields only; the current one is the release's file.
        datasets = [p for p in files if p.suffix == '.parquet']
        assert all(p.parent == SITE / 'data' for p in datasets) and SITE / 'data' / NAME in datasets
        for dataset in datasets:
            assert re.fullmatch(r'aws-announcements-\d{4}-\d{2}-\d{2}\.parquet', dataset.name), dataset.name
            columns = [r[0] for r in db.execute('describe select * from read_parquet(?)', [str(dataset)]).fetchall()]
            assert columns == FIELDS, f'{dataset.name}: fields are {columns}'
        assert (SITE / 'data' / NAME).read_bytes() == PATH.read_bytes(), 'Current dataset differs from product_change/public'

        # No page or script carries a run of words copied from saved announcement text. Titles are public fields.
        saved, titles = set(), set()
        for title, text in db.execute('select title, announcement_text from announcements').fetchall():
            saved |= shingles(text or '')
            titles |= shingles(title or '')
    for path in files:
        if path.suffix == '.parquet':
            continue
        text = path.read_text()
        if path.suffix == '.html':
            text = unescape(re.sub(r'<[^>]+>', ' ', text))
        copied = (shingles(text) & saved) - titles
        assert not copied, f'{path.relative_to(SITE)} repeats saved announcement text: {sorted(copied)[:3]}'

    # No third-party requests, cookies or storage; links between pages resolve.
    for path in files:
        if path.suffix not in {'.html', '.js', '.css'}:
            continue
        text = path.read_text()
        vendored = 'vendor' in path.relative_to(SITE).parts
        assert not re.search(r'document\.cookie|localStorage|sessionStorage|sendBeacon', text), f'{path.name}: cookie, storage or beacon use'
        if path.suffix != '.html':
            assert vendored or not re.search(r'https?://', text), f'{path.name}: names another host'
            continue
        assert "default-src 'self'" in text, f'{path.name}: no content security policy'
        for tag, target in re.findall(r'<(\w+)[^>]*?\s(?:href|src)="([^"]*)"', text):
            if re.match(r'https?://', target):
                assert tag == 'a', f'{path.name}: <{tag}> loads {target}'
            else:
                assert (path.parent / target.split('#')[0]).exists(), f'{path.name}: broken link {target}'
    index = (SITE / 'index.html').read_text()
    assert f'href="data/{NAME}"' in index, 'index.html download link does not name the current dataset'
    print(f'Checked {len(files)} files for upload: no announcement text, no third-party requests, pages current, links resolve.')


if __name__ == '__main__':
    check()
