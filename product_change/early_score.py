"""Score the 2010–2020 audit and the bridge sample from saved evidence. Offline; part of reproduction.

audit   compares each hidden-sample record's final 2010–2020 label with the blind claude-opus-5-5 reference
        reading: exact agreement per year, per level and weighted back to each year's records. This is agreement
        between AI readings, not accuracy.
bridge  compares the bridge sample's new labels, read under the two-reader protocol, with the recorded labels of
        the 2025–2026 and 2021–2024 passes: a confusion table and level shares with Wilson intervals for each pass
        and for both combined. It never changes a recorded label.

Writes early_review/audit_metrics.json, early_review/bridge_metrics.json and early_review/scores.txt.
"""
import argparse
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEW = HERE / 'early_review'
LEVELS = ['1', '2', '3', '4', '5', 'U', 'NA']
Z = 1.959963984540054


def wilson(correct, total):
    """The same Wilson score interval historical_audit.py uses."""
    if not total:
        return None
    p = correct / total
    denominator = 1 + Z * Z / total
    center = (p + Z * Z / (2 * total)) / denominator
    half = Z * math.sqrt(p * (1 - p) / total + Z * Z / (4 * total * total)) / denominator
    return [center - half, center + half]


def weighted_agreement(strata):
    """strata: {key: (population, sampled, agreeing)}. Stratified estimate weighted by population, with a normal
    95% interval using the finite-population correction, capped to 0–1."""
    total = sum(population for population, _, _ in strata.values())
    estimate = variance = 0.0
    for population, sampled, agreeing in strata.values():
        weight, p = population / total, agreeing / sampled
        estimate += weight * p
        variance += weight * weight * p * (1 - p) / sampled * (1 - sampled / population)
    half = Z * math.sqrt(variance)
    return estimate, (max(0.0, estimate - half), min(1.0, estimate + half))


def audit(sample, reference, final, populations):
    rows = [{'index': s['index'], 'year': s['date'][:4], 'source_url': s['url'], 'label': final[s['url']]['level'],
             'reference': reference[s['url']]['level']} for s in sample]
    for row in rows:
        row['exact_match'] = row['label'] == row['reference']
    by_year = {}
    for year in sorted({r['year'] for r in rows}):
        part = [r for r in rows if r['year'] == year]
        exact = sum(r['exact_match'] for r in part)
        by_year[year] = {'population': populations[year], 'sample_size': len(part), 'exact': exact,
                         'agreement': exact / len(part), 'wilson_95': wilson(exact, len(part))}
    weighted, interval = weighted_agreement({y: (m['population'], m['sample_size'], m['exact']) for y, m in by_year.items()})
    by_level = {}
    for level in LEVELS:
        correct = sum(r['label'] == r['reference'] == level for r in rows)
        predicted = sum(r['label'] == level for r in rows)
        actual = sum(r['reference'] == level for r in rows)
        by_level[level] = {'correct': correct, 'predicted': predicted, 'reference': actual,
                           'precision': correct / predicted if predicted else None, 'recall': correct / actual if actual else None}
    exact = sum(r['exact_match'] for r in rows)
    return {'sample_size': len(rows), 'population_size': sum(populations.values()), 'exact_agreement': exact,
            'unweighted_agreement': exact / len(rows), 'unweighted_wilson_95': wilson(exact, len(rows)),
            'weighted_agreement': weighted, 'weighted_95': list(interval), 'by_year': by_year, 'by_level': by_level,
            'confusion': dict(sorted(Counter(f'{r["label"]} -> {r["reference"]}' for r in rows).items())),
            'interpretation': ('This is agreement between AI readings: final labels from two claude-fable-5-2 readers with '
                               'adjudication, against one blind claude-opus-5-5 reading. It is not accuracy against human '
                               'judgement. The weighted figure weights each year by its share of the 2010–2020 records; '
                               'intervals describe sampling uncertainty only, not shared model bias.'),
            'rows': rows}


def bridge_scores(sample, new, recorded):
    def score(rows):
        exact = sum(r['recorded'] == r['new'] for r in rows)
        n = len(rows)
        recorded_counts, new_counts = Counter(r['recorded'] for r in rows), Counter(r['new'] for r in rows)
        return {'n': n, 'exact': exact, 'agreement': exact / n if n else None, 'wilson_95': wilson(exact, n),
                'confusion': dict(sorted(Counter(f'{r["recorded"]} -> {r["new"]}' for r in rows).items())),
                'levels': {level: {'recorded': recorded_counts[level], 'new': new_counts[level],
                                   'recorded_wilson_95': wilson(recorded_counts[level], n), 'new_wilson_95': wilson(new_counts[level], n)}
                           for level in LEVELS},
                'two_to_three': sum(r['recorded'] == '2' and r['new'] == '3' for r in rows),
                'three_to_two': sum(r['recorded'] == '3' and r['new'] == '2' for r in rows)}

    rows = [{'pass': s['pass'], 'source_url': s['url'], 'recorded': recorded[s['url']], 'new': new[s['url']]['level']} for s in sample]
    result = {name: score([r for r in rows if r['pass'] == name]) for name in dict.fromkeys(r['pass'] for r in rows)}
    result['combined'] = score(rows)
    return result


def early_labels():
    final = {}
    for path in sorted((REVIEW / 'labels').glob('*/final.json')):
        final.update(json.loads(path.read_text()))
    return final


def percent(value):
    return f'{value * 100:.1f}%'


def interval(bounds):
    return f'{bounds[0] * 100:.1f}–{bounds[1] * 100:.1f}%' if bounds else '—'


def main():
    import duckdb
    from early_collect import parse
    sample = json.loads((REVIEW / 'hidden_sample.json').read_text())
    reference = json.loads((REVIEW / 'reference' / 'reference.json').read_text())
    populations = Counter(r['announcement_date'][:4] for r in parse())
    metrics = audit(sample, reference, early_labels(), dict(populations))
    with duckdb.connect(str(HERE.parent / 'announcements.duckdb'), read_only=True) as db:
        recorded = dict(db.sql('select source_url, product_change_level from announcements where product_change_level is not null').fetchall())
    bridge_sample = json.loads((REVIEW / 'bridge_sample.json').read_text())
    drift = bridge_scores(bridge_sample, json.loads((REVIEW / 'bridge' / 'final.json').read_text()), recorded)
    drift['interpretation'] = ('Recorded labels against new labels for the same records, read blind under the 2010–2020 protocol. '
                               'Combined pools the two passes, 200 records each, without weighting. The bridge holds only '
                               '2021–2026 records, so it cannot detect drift specific to older texts. It changes no recorded label.')
    (REVIEW / 'audit_metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    (REVIEW / 'bridge_metrics.json').write_text(json.dumps(drift, indent=2) + '\n')

    lines = ['Audit: agreement between AI readings (2010–2020 final labels against one blind claude-opus-5-5 reading)', '',
             f'Weighted to the population: {percent(metrics["weighted_agreement"])} (95% interval {interval(metrics["weighted_95"])})',
             f'Unweighted: {metrics["exact_agreement"]}/{metrics["sample_size"]} = {percent(metrics["unweighted_agreement"])} '
             f'(Wilson {interval(metrics["unweighted_wilson_95"])})', '', f'{"Year":<6}{"Records":>9}{"Sampled":>9}{"Agree":>7}{"Rate":>8}  Wilson 95%']
    for year, m in metrics['by_year'].items():
        lines.append(f'{year:<6}{m["population"]:>9}{m["sample_size"]:>9}{m["exact"]:>7}{percent(m["agreement"]):>8}  {interval(m["wilson_95"])}')
    lines += ['', f'{"Level":<6}{"Label":>7}{"Reference":>11}{"Both":>6}{"Precision":>11}{"Recall":>8}']
    for level, m in metrics['by_level'].items():
        lines.append(f'{level:<6}{m["predicted"]:>7}{m["reference"]:>11}{m["correct"]:>6}'
                     f'{percent(m["precision"]) if m["precision"] is not None else "—":>11}{percent(m["recall"]) if m["recall"] is not None else "—":>8}')
    lines += ['', metrics['interpretation'], '', 'Bridge: recorded labels against new labels for the same records', '']
    for name in [k for k in drift if k != 'interpretation']:
        d = drift[name]
        lines += [f'{name}: {d["exact"]}/{d["n"]} = {percent(d["agreement"])} agree (Wilson {interval(d["wilson_95"])}); '
                  f'2 -> 3: {d["two_to_three"]}, 3 -> 2: {d["three_to_two"]}',
                  '  rows recorded, columns new: ' + '  '.join(LEVELS)]
        for old in LEVELS:
            cells = [d['confusion'].get(f'{old} -> {level}', 0) for level in LEVELS]
            if any(cells):
                lines.append(f'  {old:<3}' + ''.join(f'{c:>4}' for c in cells))
        lines.append('  level shares, recorded vs new (Wilson 95%): ' + '; '.join(
            f'{level} {interval(v["recorded_wilson_95"])} vs {interval(v["new_wilson_95"])}' for level, v in d['levels'].items() if v['recorded'] or v['new']))
        lines.append('')
    lines.append(drift['interpretation'])
    (REVIEW / 'scores.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    main()
