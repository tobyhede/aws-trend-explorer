"""Deterministic SVG charts from exported, source-reviewed DuckDB counts."""
import csv
import html
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEVELS = ['1', '2', '3', '4', '5', 'U', 'NA']
NAMES = {'1': 'Parameter change', '2': 'Capability refinement', '3': 'New capability',
         '4': 'Major product expansion', '5': 'New product', 'U': 'Needs review', 'NA': 'Outside scale'}
COLORS = {'1': '#b6cfcd', '2': '#619d98', '3': '#116d68', '4': '#d99136', '5': '#963e28', 'U': '#9b81a6', 'NA': '#d9dddf'}


def chart(source, destination, key, title, subtitle):
    with (HERE / source).open() as stream:
        rows = list(csv.DictReader(stream))
    periods = sorted({r[key] for r in rows})
    counts = {(r[key], r['level']): int(r['announcements']) for r in rows}
    maximum = max(sum(counts.get((p, k), 0) for k in LEVELS) for p in periods)
    width, height, left, top, plot_height = 1200, 650, 65, 140, 360
    step = 1100 / len(periods)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
             f'<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(subtitle)}. Counts by product-change level; exact values in each bar title and companion CSV.</desc>',
             f'<rect width="{width}" height="{height}" fill="#f5f5ef"/><g font-family="Arial,sans-serif" fill="#203a3d">',
             f'<text x="35" y="40" font-size="27">{html.escape(title)}</text><text x="35" y="72" font-size="16">{html.escape(subtitle)}</text>']
    x = 35
    for level in LEVELS:
        label = NAMES[level]
        parts.append(f'<rect x="{x}" y="96" width="12" height="12" fill="{COLORS[level]}"/><text x="{x+17}" y="107" font-size="12">{label}</text>')
        x += 17 + len(label) * 6.7 + 18
    for tick in range(5):
        value = maximum * tick / 4
        y = top + plot_height * (1 - tick / 4)
        parts.append(f'<line x1="{left}" x2="1165" y1="{y}" y2="{y}" stroke="#d4ddda"/><text x="{left-10}" y="{y+5}" text-anchor="end" font-size="13">{round(value):,}</text>')
    for index, period in enumerate(periods):
        bottom = top + plot_height
        for level in LEVELS:
            n = counts.get((period, level), 0)
            if not n:
                continue
            h = plot_height * n / maximum
            bottom -= h
            parts.append(f'<rect x="{left+index*step+2:.3f}" y="{bottom:.3f}" width="{max(1,step-4):.3f}" height="{h:.3f}" fill="{COLORS[level]}"><title>{period}: {NAMES[level]} — {n:,}</title></rect>')
        if len(periods) <= 12 or period.endswith('-01'):
            parts.append(f'<text x="{left+index*step+step/2:.3f}" y="525" font-size="13" text-anchor="middle">{period[:4]}</text>')
        if len(periods) <= 12:
            total = sum(counts.get((period, k), 0) for k in LEVELS)
            parts.append(f'<text x="{left+index*step+step/2:.3f}" y="{bottom-8:.3f}" font-size="14" text-anchor="middle">{total:,}</text>')
    parts.extend(['<text x="35" y="565" font-size="15">Source: collected official AWS What’s New announcements. AI source judgments; see historical_review/report.html.</text>',
                  '<text x="35" y="592" font-size="15">Outside scale includes regional rollout, pricing-only, compliance and non-product announcements.</text>',
                  '<text x="35" y="619" font-size="15">Magnitude describes the change itself. Historical source coverage is spot-checked, not proven exhaustive.</text></g></svg>'])
    (HERE / destination).write_text(''.join(parts))


def charts():
    chart('matched.csv', 'annual.svg', 'year', 'AWS product-change magnitude · matched annual periods', 'January 1–October 28 each year · 2021–2026 · announcement counts')
    chart('annual.csv', 'annual_full.svg', 'year', 'AWS product-change magnitude · calendar-year totals', '2021–2025 complete calendar periods; 2026 ends October 28 and is not directly comparable')
    chart('monthly.csv', 'monthly.svg', 'month', 'AWS product-change magnitude · monthly publication volume', 'January 2021–October 28, 2026 · last month is partial · announcement counts')


if __name__ == '__main__':
    charts()
