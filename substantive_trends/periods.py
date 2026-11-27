"""Compare substantive output across the pre-COVID (2010–2019), COVID (2020–2021) and post-COVID (2022–2026)
periods from the built corpus. Needs only DuckDB; reads announcements.duckdb read-only.

Every figure uses the matched period, 1 January – 28 October, in every year. Levels are ordered categories:
no average level, no weighted score, no counterfactual and no service breakdown. "Strict" is levels 3–5 and
"broad" is levels 2–5, as in recalculate.py; both are analysis thresholds, not rubric levels.

Writes periods.json and periods.txt beside this script.
"""
import json
import math
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEVELS = ['1', '2', '3', '4', '5', 'U', 'NA']
STRICT, BROAD = {'3', '4', '5'}, {'2', '3', '4', '5'}
PERIODS = {'pre-COVID': (2010, 2019), 'COVID': (2020, 2021), 'post-COVID': (2022, 2026)}
SENSITIVITY = (2015, 2019)
SERIES = ['announcements', 'strict', 'broad']
Z = 1.959963984540054


def wilson(count, total):
    if not total:
        return None
    p = count / total
    denominator = 1 + Z * Z / total
    center = (p + Z * Z / (2 * total)) / denominator
    half = Z * math.sqrt(p * (1 - p) / total + Z * Z / (4 * total * total)) / denominator
    return [center - half, center + half]


def matched(day):
    return day[5:] <= '10-28'


def tables(rows, periods=PERIODS, sensitivity=SENSITIVITY):
    """rows: (YYYY-MM-DD, level). Returns the annual series, median year-on-year changes and level shares."""
    rows = [(int(day[:4]), level) for day, level in rows if matched(day)]
    first, last = min(start for start, _ in periods.values()), max(end for _, end in periods.values())
    by_year = {year: Counter(level for y, level in rows if y == year) for year in range(first, last + 1)}
    annual = [{'year': year, 'announcements': sum(c.values()), 'strict': sum(c[l] for l in STRICT), 'broad': sum(c[l] for l in BROAD)}
              for year, c in by_year.items()]
    series = {r['year']: r for r in annual}

    def change(year, name):
        """Percent change from the previous year; None without a previous year or with a zero base."""
        previous = series.get(year - 1)
        if not previous or not previous[name]:
            return None
        return 100 * (series[year][name] / previous[name] - 1)

    windows = dict(periods)
    windows[f'{sensitivity[0]}–{sensitivity[1]}'] = sensitivity
    median_change = []
    for name, (start, end) in windows.items():
        row = {'period': name, 'first': start, 'last': end,
               'years': [y for y in range(start, end + 1) if change(y, 'announcements') is not None]}
        for s in SERIES:
            values = [v for y in range(start, end + 1) if (v := change(y, s)) is not None]
            row[s] = statistics.median(values) if values else None
            row[s + '_changes'] = len(values)
        median_change.append(row)
    shares = []
    for name, (start, end) in periods.items():
        counts = Counter(level for year, level in rows if start <= year <= end)
        total = sum(counts.values())
        shares += [{'period': name, 'level': level, 'count': counts[level], 'total': total,
                    'share': counts[level] / total if total else None, 'wilson_95': wilson(counts[level], total)} for level in LEVELS]
    return {'annual': annual, 'median_change': median_change, 'shares': shares}


def reader_context():
    """Audit agreement for each labelling pass and the bridge sample's drift, printed beside the shares."""
    early = json.loads((ROOT / 'product_change/early_review/audit_metrics.json').read_text())
    historical = json.loads((ROOT / 'product_change/historical_review/metrics.json').read_text())
    recent = json.loads((ROOT / 'product_change/review_report.json').read_text())
    bridge = json.loads((ROOT / 'product_change/early_review/bridge_metrics.json').read_text())
    shares = {}
    for name in ('2025-2026', '2021-2024', 'combined'):
        d = bridge[name]
        shares[name] = {'agreement': d['agreement'], 'wilson_95': d['wilson_95'], 'n': d['n'],
                        'two_to_three': d['two_to_three'], 'three_to_two': d['three_to_two'],
                        'level_3_recorded': d['levels']['3']['recorded'] / d['n'], 'level_3_new': d['levels']['3']['new'] / d['n'],
                        'strict_recorded': sum(d['levels'][l]['recorded'] for l in STRICT) / d['n'],
                        'strict_new': sum(d['levels'][l]['new'] for l in STRICT) / d['n']}
    coverage = json.loads((ROOT / 'product_change/early_snapshot/coverage.json').read_text())['years']
    return {'coverage': {str(r['year']): r['absent_count'] for r in coverage},
            'audit': {
                '2010-2020': {'agreement': early['weighted_agreement'], 'interval_95': early['weighted_95'],
                              'basis': 'final labels against one blind claude-opus-5-5 reading, 300 records, weighted to each year'},
                '2021-2024': {'agreement': historical['agreement_rate'], 'interval_95': historical['wilson_95'],
                              'basis': 'initial ratings against a blind adjudicated AI reference, 200 records, before corrections'},
                '2025-2026': {'agreement': recent['independent_exact_agreement'] / recent['sample_size'], 'interval_95': wilson(recent['independent_exact_agreement'], recent['sample_size']),
                              'basis': 'first reading against an independent reading, 120 records, before adjudication'}},
            'bridge': shares,
            'protocols': {'pre-COVID': '2010–2019: two-reader protocol (2026-11-27)',
                          'COVID': '2020: two-reader protocol; 2021: historical pass (2026-11-25)',
                          'post-COVID': '2022–2024: historical pass; 2025–2026: recent pass (2026-11-24)'}}


def pct(value, digits=1):
    return '—' if value is None else f'{value * 100:.{digits}f}%'


def signed(value):
    return '—' if value is None else f'{value:+.1f}%'


def interval(bounds):
    return '—' if not bounds else f'{bounds[0] * 100:.1f}–{bounds[1] * 100:.1f}%'


def render(result, context):
    lines = ['Substantive output by period (matched period, 1 January – 28 October, every year)', '',
             'Table 1. Annual series', f'{"Year":<6}{"Announcements":>15}{"Levels 3–5":>12}{"Levels 2–5":>12}']
    lines += [f'{r["year"]:<6}{r["announcements"]:>15,}{r["strict"]:>12,}{r["broad"]:>12,}' for r in result['annual']]
    lines += ['', 'Table 2. Median year-on-year change (changes ending in each year of the window; the first year of the corpus has none)',
              f'{"Window":<14}{"Years":>11}{"Announcements":>15}{"Levels 3–5":>12}{"Levels 2–5":>12}']
    for r in result['median_change']:
        lines.append(f'{r["period"]:<14}{str(r["first"]) + "–" + str(r["last"]):>11}{signed(r["announcements"]):>15}{signed(r["strict"]):>12}{signed(r["broad"]):>12}')
    lines += ['', 'Table 3. Share of announcements at each level (Wilson 95% interval)', f'{"Level":<7}' + ''.join(f'{p:>26}' for p in PERIODS)]
    for level in LEVELS:
        cells = [next(r for r in result['shares'] if r['period'] == p and r['level'] == level) for p in PERIODS]
        lines.append(f'{level:<7}' + ''.join(f'{pct(c["share"]) + " (" + interval(c["wilson_95"]) + ")":>26}' for c in cells))
    totals = [next(r for r in result['shares'] if r['period'] == p)['total'] for p in PERIODS]
    lines.append(f'{"Total":<7}' + ''.join(f'{t:>26,}' for t in totals))
    lines += ['', 'Beside Table 3: reader agreement and drift', 'Audit agreement, between AI readings:']
    for name, a in context['audit'].items():
        lines.append(f'  {name}: {pct(a["agreement"])} ({interval(a["interval_95"])}); {a["basis"]}')
    lines.append('Bridge sample, recorded labels against the 2010–2020 protocol on the same records:')
    for name, b in context['bridge'].items():
        lines.append(f'  {name}: {pct(b["agreement"])} agree ({interval(b["wilson_95"])}), n={b["n"]}; level 2 to 3: {b["two_to_three"]}, 3 to 2: {b["three_to_two"]}; '
                     f'level 3 share {pct(b["level_3_recorded"])} recorded vs {pct(b["level_3_new"])} new; levels 3–5 {pct(b["strict_recorded"])} vs {pct(b["strict_new"])}')
    absent = context['coverage']
    lines.append('Coverage, 2010–2020: announcement links on archived yearly index pages that the AWS directory API no longer lists: '
                 + ', '.join(f'{y} {"unchecked" if n is None else n}' for y, n in absent.items()) + '. 2021–2026 coverage rests on the earlier collection checks.')
    lines.append('Labelling protocol by period:')
    lines += [f'  {k}: {v}' for k, v in context['protocols'].items()]
    return '\n'.join(lines) + '\n'


NUMBER = r'(?<![\d.])[+-]?\d+(?:,\d{3})*(?:\.\d+)?%?'  # a sign only where no digit precedes it, as in 2021-2024


def check_report(report, tables_text):
    """Every number in the written interpretation must appear in the computed tables."""
    import re
    available = set(re.findall(NUMBER, tables_text))
    missing = sorted({n for n in re.findall(NUMBER, report) if n not in available and n.lstrip('+-') not in available})
    assert not missing, f'numbers in the interpretation that are not in the tables: {missing}'


def main():
    import duckdb
    with duckdb.connect(str(ROOT / 'announcements.duckdb'), read_only=True) as db:
        rows = db.sql("select cast(announcement_date as varchar), product_change_level from announcements where product_change_level is not null").fetchall()
    assert len(rows) == 22588, len(rows)
    result = tables(rows)
    context = reader_context()
    (HERE / 'periods.json').write_text(json.dumps({**result, 'reader_context': context}, indent=2) + '\n')
    text = render(result, context)
    (HERE / 'periods.txt').write_text(text)
    print(text)
    report = HERE / 'PERIODS_REPORT.md'
    if report.exists():
        check_report(report.read_text(), text)
        print('PERIODS_REPORT.md uses only numbers from these tables.')


if __name__ == '__main__':
    main()
