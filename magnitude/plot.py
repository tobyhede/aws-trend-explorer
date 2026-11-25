"""Write a standalone SVG year-over-year figure from the matched counts."""
import csv
from pathlib import Path
P=Path(__file__).resolve().parent
def plot():
    with (P/'matched.csv').open() as f:
        rows={(int(r['year']),r['rating']):r for r in csv.DictReader(f)}
    names={'1':'Local adjustment','2':'Workflow change','3':'Architecture change','U':'Unrated'}
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 350" style="background:#f8f9f4;font:15px sans-serif;fill:#173934"><rect width="760" height="350" fill="#f8f9f4"/><text x="25" y="38" font-size="24">What changed for the affected workload?</text><text x="25" y="67">Share of enhancement announcements · January 1–October 28 in each year</text>']
    mx=max(float(r['share_percent']) for r in rows.values()) or 1
    for j,(k,label) in enumerate(names.items()):
        y=102+j*62
        parts.append(f'<text x="25" y="{y+13}">{label}</text>')
        for i,(year,color) in enumerate([(2025,'#a2bdb1'),(2026,'#086c67')]):
            r=rows[year,k]; width=300*float(r['share_percent'])/mx; py=y+18*i
            parts.append(f'<rect x="204" y="{py-9}" width="{width:.2f}" height="11" fill="{color}"/><text x="520" y="{py+2}">{year} · {float(r["share_percent"]):.1f}% ({r["enhancements"]})</text>')
    (P/'matched.svg').write_text(''.join(parts)+'</svg>')
if __name__=='__main__':plot()
