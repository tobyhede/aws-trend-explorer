"""Write the hosted explorer's supporting pages into hosted/site/.

Usage: .venv/bin/python hosted/pages.py

The method page and the two audit reports are copied from the release's own reports, with links to
material that is not published removed. The data guide and release notes come from hosted/pages/,
which are the versions limited to the nine public fields. hosted/check_site.py confirms that the
written pages are current and hold no announcement text.
"""
import re
from pathlib import Path
import duckdb

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = HERE / 'site'
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

# (source report, output page, exact replacements). Each replacement must match exactly once,
# so a changed source report stops the build instead of publishing an unreviewed page.
SOURCED = [
    ('product_change/method.html', 'method.html', [
        (' <a href="/product-change-review">Read the audit and its limitations</a>.', ''),
        ('<a href="/historical-product-audit">', '<a href="historical-audit.html">'),
    ]),
    ('product_change/historical_review/report.html', 'historical-audit.html', [
        ('<p><a href="/historical-audit.csv">Download row-level audit CSV</a> · <a href="/historical-audit-metrics.json">Audit metrics JSON</a></p>', ''),
    ]),
    ('product_change/fresh_accuracy/report.html', 'fresh-audit.html', []),
]
WRITTEN = ['data-guide.html', 'release-notes.html']
NAV = [('index.html', 'Hosted explorer'), ('method.html', 'Method'), ('historical-audit.html', 'Historical audit'),
       ('fresh-audit.html', 'Fresh-sample audit'), ('data-guide.html', 'Data guide'), ('release-notes.html', 'Release notes')]

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="no-referrer">
<title>{title} · AWS announcement explorer</title>
<link rel="stylesheet" href="site.css">
</head>
<body>
<main class="doc">
<nav aria-label="Site">{nav}</nav>
{body}
<footer>
  <p>Release {release}. Collection cutoff {cutoff}.</p>
  <p>The magnitude levels, reasons and bases are classifications by Toby Hede, offered under the <a href="https://creativecommons.org/licenses/by/4.0/" rel="license noreferrer">Creative Commons Attribution 4.0 International licence (CC BY 4.0)</a>. To reuse them, credit “Toby Hede, AWS announcement explorer” and link to this site. Announcement titles and the linked announcement pages remain the property of Amazon Web Services and are outside that licence.</p>
  <p>This site is not affiliated with, sponsored by or endorsed by Amazon Web Services. It sets no cookies and loads nothing from other sites.</p>
</footer>
</main>
</body>
</html>
"""


def long_date(iso):
    year, month, day = iso.split('-')
    return f'{int(day)} {MONTHS[int(month) - 1]} {year}'


def release():
    """The release values, read from the hosted explorer's single source: site/release.js."""
    source = (SITE / 'release.js').read_text()
    values = {key: re.search(rf"{key}: '(\d{{4}}-\d{{2}}-\d{{2}})'", source).group(1) for key in ['date', 'first', 'cutoff']}
    name = f"aws-announcements-{values['date']}.parquet"
    with duckdb.connect() as db:
        records = db.execute('select count(*) from read_parquet(?)', [str(SITE / 'data' / name)]).fetchone()[0]
    return {'release': long_date(values['date']), 'first': long_date(values['first']), 'cutoff': long_date(values['cutoff']),
            'cutoff_day': long_date(values['cutoff']).rsplit(' ', 1)[0], 'cutoff_mmdd': values['cutoff'][5:],
            'dataset': 'data/' + name, 'dataset_name': name, 'records': f'{records:,}'}


def wrap(body, name, values):
    title = re.sub(r'<[^>]+>', '', re.search(r'<h1>(.*?)</h1>', body, re.S).group(1))
    nav = ''.join(f'<a href="{href}"' + (' aria-current="page"' if href == name else '') + f'>{label}</a>' for href, label in NAV)
    return TEMPLATE.format(title=title, nav=nav, body=body.strip(), release=values['release'], cutoff=values['cutoff'])


def render():
    """Return {file name: page text} for every supporting page."""
    values = release()
    pages = {}
    for source, name, replacements in SOURCED:
        body = (ROOT / source).read_text().split('</style>', 1)[1]
        for old, new in replacements:
            assert body.count(old) == 1, f'{source}: expected exactly one {old!r}'
            body = body.replace(old, new)
        assert 'href="/' not in body, f'{source}: a link to the local explorer remains'
        pages[name] = wrap(body, name, values)
    for name in WRITTEN:
        body = (HERE / 'pages' / name).read_text()
        for key, value in values.items():
            body = body.replace('{' + key + '}', value)
        assert not re.search(r'\{[a-z_]+\}', body), f'{name}: unfilled placeholder'
        pages[name] = wrap(body, name, values)
    return pages


if __name__ == '__main__':
    for name, text in render().items():
        (SITE / name).write_text(text)
        print('Wrote', (SITE / name).relative_to(ROOT))
