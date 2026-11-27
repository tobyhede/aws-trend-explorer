// Development-only check: the hosted explorer's JavaScript counting must match the released, verified outputs.
// Run from the repository root: node hosted/check.mjs
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parquetMetadataAsync, parquetReadObjects } from './site/vendor/hyparquet/index.js';
import { RELEASE, DATASET } from './site/release.js';
import { prepare, summarize, select, choices, months, sharePercent, toCsv, untagged, periodOf, FIELDS, PERIODS } from './site/counting.js';

const here = dirname(fileURLToPath(import.meta.url));
const root = dirname(here);
const csv = name => {
  const [header, ...lines] = readFileSync(join(root, 'product_change', name), 'utf8').trim().split(/\r?\n/);
  const fields = header.split(',');
  return lines.map(line => Object.fromEntries(line.split(',').map((value, i) => [fields[i], value])));
};
// Flatten {a:{b:n}} into sorted "a,b,n" lines, dropping zero counts, so results compare with aggregate CSV rows.
const flat = (nested, prefix = []) => Object.entries(nested).flatMap(([key, value]) =>
  typeof value === 'object' ? flat(value, [...prefix, key]) : value ? [[...prefix, key, value].join(',')] : []).sort();
const released = (name, fields) => csv(name).map(r => fields.map(f => r[f]).join(',')).sort();

// The hosted copy is the released file, byte for byte.
const hosted = readFileSync(join(here, 'site', DATASET));
const bundled = readFileSync(join(root, 'product_change', 'public', DATASET.split('/').pop()));
assert.ok(hosted.equals(bundled), 'hosted/site/data copy differs from product_change/public: rerun product_change/public_dataset.py');

const file = hosted.buffer.slice(hosted.byteOffset, hosted.byteOffset + hosted.byteLength);
const metadata = await parquetMetadataAsync(file);
const stored = Object.fromEntries(metadata.key_value_metadata.map(kv => [kv.key, kv.value]));
assert.equal(stored.release_date, RELEASE.date);
assert.equal(stored.collection_cutoff, RELEASE.cutoff);
const rows = await parquetReadObjects({ file, metadata });
assert.deepEqual(Object.keys(rows[0]), FIELDS);
const records = prepare(rows);
assert.equal(records.length, 22588);

// Ticket 02: annual matched-period counts equal matched.csv.
const all = summarize(records, {}, RELEASE);
assert.equal(all.total, 22588);
assert.deepEqual(flat(all.annual), released('matched.csv', ['year', 'level', 'announcements']));
const inScale = Object.fromEntries(all.years.map(y => [y.year, y.inScale]));
for (const y of all.years) {
  const expected = csv('matched.csv').filter(r => +r.year === y.year && r.level !== 'NA').reduce((sum, r) => sum + +r.announcements, 0);
  assert.equal(y.inScale, expected, `in-scale total ${y.year}`);
}
assert.equal(all.years[0].change, null);
assert.equal(all.years.at(-1).change, inScale[2026] / inScale[2025] - 1);

// Ticket 03: monthly counts equal monthly.csv, and every month of the release is present.
assert.deepEqual(flat(all.monthly), released('monthly.csv', ['month', 'level', 'announcements']));
const allMonths = months(RELEASE);
assert.equal(allMonths.length, 202);
assert.deepEqual([allMonths[0], allMonths.at(-1)], ['2010-01', '2026-10']);
assert.deepEqual(all.years.map(y => y.year), Array.from({ length: 17 }, (_, i) => 2010 + i));
assert.deepEqual(Object.keys(all.monthly), allMonths);
// The share denominator is all filtered announcements in the month, including needs-review and outside-scale.
for (const month of allMonths) {
  const expected = csv('monthly.csv').filter(r => r.month === month).reduce((sum, r) => sum + +r.announcements, 0);
  assert.equal(all.monthlyTotals[month], expected, `monthly total ${month}`);
}
assert.equal(sharePercent(38, all.monthlyTotals['2021-01']), 100 * 38 / 116);
assert.equal(sharePercent(0, 0), null);

// Ticket 04: the per-service matched comparison equals service_matched.csv, both as a breakdown and through the service filter.
const serviceRows = csv('service_matched.csv');
assert.deepEqual(flat(all.breakdown.service).map(line => { const [tag, year, level, n] = line.split(','); return [year, tag, level, n].join(','); }).sort(),
  released('service_matched.csv', ['year', 'service', 'level', 'announcements']));
const options = choices(records);
// Services announced only after 28 October of a year are choices too, with empty matched-period counts.
assert.ok(serviceRows.every(r => options.service.includes(r.service)));
for (const service of options.service) {
  assert.deepEqual(flat(summarize(records, { service }, RELEASE).annual),
    serviceRows.filter(r => r.service === service).map(r => [r.year, r.level, r.announcements].join(',')).sort(), `service filter ${service}`);
}

// Ticket 04: a fixed set of filters gives the same summary as the local explorer (serve.overview).
const queries = [{}, { type: 'enhancement' }, { type: 'new_product' }, { service: 'amazon-ec2' }, { service: 'unknown' },
  { facet: 'integration_compatibility' }, { facet: 'service_limit' },
  { type: 'enhancement', service: 'amazon-bedrock', facet: 'performance' }, { type: 'availability_expansion', service: 'aws-govcloud-us' }];
const python = process.env.PYTHON || join(root, '.venv', 'bin', 'python');
assert.ok(existsSync(python), `Python with duckdb not found at ${python}; set PYTHON`);
const local = JSON.parse(execFileSync(python, [join(here, 'local_summaries.py'), JSON.stringify(queries)], { maxBuffer: 1 << 28 }));
queries.forEach((query, i) => {
  const ours = summarize(records, query, RELEASE), theirs = local[i], label = JSON.stringify(query);
  assert.equal(ours.total, theirs.total, label);
  assert.deepEqual(flat(ours.annual), theirs.product_annual.map(r => [r.year, r.level, r.n].join(',')).sort(), label);
  assert.deepEqual(flat(ours.monthly), theirs.product_monthly.map(r => [r.month, r.level, r.n].join(',')).sort(), label);
  assert.deepEqual(ours.years.map(y => ({ year: y.year, matched: y.matched, total: y.total })), theirs.annual, label);
  for (const key of ['type', 'service', 'facet']) {
    const perYear = year => Object.fromEntries(Object.entries(ours.breakdown[key])
      .map(([tag, years]) => [tag, Object.values(years[year] || {}).reduce((a, b) => a + b, 0)]));
    const previous = perYear(2025), current = perYear(2026);
    assert.deepEqual(Object.keys(previous).filter(tag => previous[tag] + current[tag]).map(tag => [tag, previous[tag], current[tag]].join(',')).sort(),
      theirs.breakdown[key].map(r => [r.tag, r.previous, r.current].join(',')).sort(), `${label} ${key}`);
  }
  // Ticket 05: the records behind every count are exactly as many as the count.
  for (const [year, levels] of Object.entries(ours.annual)) for (const [level, n] of Object.entries(levels))
    assert.equal(select(records, query, RELEASE, { year: +year, level }).length, n, `${label} ${year} ${level}`);
  for (const [month, levels] of Object.entries(ours.monthly)) for (const [level, n] of Object.entries(levels))
    assert.equal(select(records, query, RELEASE, { month, level }).length, n, `${label} ${month} ${level}`);
  assert.equal(select(records, query, RELEASE).length, ours.total, label);
});
assert.deepEqual(options.type, local[0].options.type);

// Ticket 10: the page's three periods are the analysis periods, cover every year once, and records without a service tag count as unknown.
const analysisPeriods = JSON.parse(execFileSync(python, ['-c', 'import json,sys; sys.path.insert(0, "substantive_trends"); import periods; print(json.dumps(periods.PERIODS))'], { cwd: root }));
assert.deepEqual(PERIODS.map(p => [p.name, [p.first, p.last]]), Object.entries(analysisPeriods));
assert.deepEqual(all.years.map(y => periodOf(y.year)?.name), all.years.map(y => PERIODS.find(p => y.year >= p.first && y.year <= p.last).name));
assert.equal(PERIODS[0].first, +RELEASE.first.slice(0, 4));
assert.equal(PERIODS.at(-1).last, +RELEASE.cutoff.slice(0, 4));
PERIODS.slice(1).forEach((p, i) => assert.equal(p.first, PERIODS[i].last + 1));
assert.ok(records.every(r => r.services.length));
const missing = untagged(records, RELEASE);
assert.deepEqual(Object.entries(missing).map(([year, c]) => [+year, c.n, c.missing]), local[0].untagged.map(r => [r.year, r.n, r.missing]));
assert.ok(missing[2010].missing / missing[2010].n > 0.9, 'most 2010 records have no service tag');
assert.deepEqual(options.facet, local[0].options.facet);
assert.deepEqual(options.service, local[0].options.service);

// Ticket 04: search is a case-insensitive substring match over title and reason only.
const hits = select(records, { q: 'LaMbDa' }, RELEASE);
const expectedHits = rows.filter(r => (r.title + '\n' + r.product_change_reason).toLowerCase().includes('lambda')).length;
assert.ok(expectedHits > 100 && hits.length === expectedHits);
assert.equal(summarize(records, { q: 'lambda' }, RELEASE).total, expectedHits);
assert.equal(select(records, { q: 'historical_source_review' }, RELEASE).length, 0, 'basis is not searched');

// Ticket 05: newest first, in the local explorer's order; the selection respects the matched period and partial month.
const ordered = select(records, { service: 'amazon-s3' }, RELEASE);
assert.deepEqual(ordered.map(r => r.url), local[0].s3_order);
assert.ok(select(records, {}, RELEASE, { year: 2025, level: '2' }).every(r => r.date >= '2025-01-01' && r.date <= '2025-10-28' && r.level === '2'));
assert.ok(select(records, {}, RELEASE, { month: '2026-10', level: 'NA' }).every(r => r.date.startsWith('2026-10') && r.level === 'NA'));

// Ticket 05: CSV export holds the nine public fields and survives commas, quotes and line breaks.
const exported = toCsv(ordered);
assert.equal(exported.split('\r\n')[0], FIELDS.join(','));
assert.equal(toCsv([{ ...ordered[0], title: 'a "b", c\nd' }]).split('\r\n').slice(1).join('\r\n').split(',')[1].startsWith('"a ""b""'), true);
assert.equal(exported.trimEnd().split('\r\n').length, ordered.length + 1);
assert.ok(ordered.some(r => r.services.length > 1) && exported.includes('; '));

console.log(`Hosted explorer counts match matched.csv, monthly.csv, service_matched.csv and ${queries.length} local explorer summaries for all 22,588 records.`);
