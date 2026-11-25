"""Export product-change counts and a portable chart from the reviewed DuckDB rows."""
import csv
import html
from pathlib import Path
import duckdb

HERE = Path(__file__).resolve().parent
NAMES = {'1': 'Parameter change', '2': 'Capability refinement', '3': 'New capability',
         '4': 'Major product expansion', '5': 'New product', 'U': 'Needs review', 'NA': 'Outside scale'}


def charts():
    with duckdb.connect(str(HERE.parent / 'announcements.duckdb'), read_only=True) as db:
        queries = {
            'annual': "select year(announcement_date) AS year, product_change_level AS level, count(*) AS announcements from announcements where product_change_level is not null group by 1,2 order by 1,2",
            'monthly': "select strftime(announcement_date,'%Y-%m') AS month, product_change_level AS level, count(*) AS announcements from announcements where product_change_level is not null group by 1,2 order by 1,2",
            'service_matched': "select year(a.announcement_date) AS year, tag AS service, a.product_change_level AS level, count(*) AS announcements from announcements a, unnest(string_split(a.service,'; ')) as tags(tag) where a.product_change_level is not null and strftime(a.announcement_date,'%m-%d')<='10-28' group by 1,2,3 order by 1,2,3",
        }
        for name, sql in queries.items():
            cur = db.execute(sql)
            with (HERE / (name + '.csv')).open('w', newline='') as f:
                writer = csv.writer(f); writer.writerow([x[0] for x in cur.description]); writer.writerows(cur.fetchall())
        counts = {(str(y), level): n for y, level, n in db.sql("select year(announcement_date),product_change_level,count(*) from announcements where product_change_level is not null and strftime(announcement_date,'%m-%d')<='10-28' group by 1,2").fetchall()}
    levels = ['1', '2', '3', '4', '5', 'U']
    maximum = max(counts.get((year, level), 0) for year in ['2025', '2026'] for level in levels)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1050 680" role="img" aria-labelledby="title desc">',
             '<title id="title">AWS product-change announcements: matched 2025 and 2026 periods</title>',
             '<desc id="desc">Counts by reviewed product-change level for January 1 through October 28 of each year. Excluded announcements shown in footer.</desc>',
             '<rect width="1050" height="680" fill="#f5f5ef"/><g font-family="Arial,sans-serif" fill="#203a3d">',
             '<text x="35" y="45" font-size="27">Scope of the AWS product change</text>',
             '<text x="35" y="76" font-size="16">January 1–October 28 in each year · source-reviewed announcement counts</text>',
             '<rect x="725" y="96" width="15" height="15" fill="#789797"/><text x="747" y="109" font-size="15">2025</text>',
             '<rect x="825" y="96" width="15" height="15" fill="#086c67"/><text x="847" y="109" font-size="15">2026</text>']
    for index, level in enumerate(levels):
        y = 150 + index * 73
        parts.append(f'<text x="35" y="{y+22}" font-size="16">{html.escape(NAMES[level])}</text>')
        for offset, year, color in [(0, '2025', '#789797'), (26, '2026', '#086c67')]:
            n = counts.get((year, level), 0); width = 610 * n / maximum
            parts.append(f'<rect x="280" y="{y+offset}" width="{width:.2f}" height="19" fill="{color}"/><text x="{290+width:.2f}" y="{y+offset+15}" font-size="14">{n:,}</text>')
    excluded = ' · '.join(f'{year}: {counts.get((year,"NA"),0):,}' for year in ['2025','2026'])
    parts.append(f'<text x="35" y="607" font-size="15">Outside scale — {excluded}</text>')
    parts.append('<text x="35" y="634" font-size="14">AI source judgments; see review.html for the independent sample and limitations.</text>')
    parts.append('<text x="35" y="658" font-size="14">Levels describe announced changes, not engineering effort or customer impact.</text></g></svg>')
    (HERE / 'matched.svg').write_text(''.join(parts))
    from history_charts import charts as historical_charts
    historical_charts()
    print('Wrote annual, monthly, service-matched CSVs and four SVG charts from DuckDB.')


if __name__ == '__main__':
    charts()
