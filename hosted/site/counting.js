// All filtering and counting for the hosted explorer. Touches no page elements, so Node can check it
// against the released aggregate files (hosted/check.mjs). The rules mirror the local explorer:
// - matched period: 1 January to the cutoff's month and day, in every year;
// - in-scale totals include U (needs review) and exclude NA (outside scale);
// - levels are ordered categories and are only ever counted, never weighted;
// - service tags and enhancement facets are multi-valued, and a record counts once per tag.

export const FIELDS = ['announcement_date', 'title', 'service', 'release_type', 'enhancement_facets',
  'product_change_level', 'product_change_reason', 'product_change_basis', 'source_url'];
export const LEVELS = ['1', '2', '3', '4', '5', 'U', 'NA'];
export const LEVEL_NAMES = { 1: 'Parameter change', 2: 'Capability refinement', 3: 'New capability',
  4: 'Major product expansion', 5: 'New product', U: 'Needs review', NA: 'Outside scale' };

// The three analysis periods (GLOSSARY.md; substantive_trends/periods.py). The COVID period is counted in neither of the others.
export const PERIODS = [
  { name: 'pre-COVID', label: 'Pre-COVID', first: 2010, last: 2019 },
  { name: 'COVID', label: 'COVID', first: 2020, last: 2021 },
  { name: 'post-COVID', label: 'Post-COVID', first: 2022, last: 2026 },
];
export const periodOf = year => PERIODS.find(p => year >= p.first && year <= p.last);

const isoDate = value => value instanceof Date ? value.toISOString().slice(0, 10) : String(value).slice(0, 10);

/** Turn the public dataset's rows into records with split multi-valued fields. */
export function prepare(rows) {
  return rows.map(row => {
    const title = row.title ?? '', reason = row.product_change_reason ?? '';
    return {
      date: isoDate(row.announcement_date),
      title,
      services: row.service ? row.service.split('; ') : [],
      type: row.release_type,
      facets: row.enhancement_facets ? row.enhancement_facets.split('|') : [],
      level: row.product_change_level,
      reason,
      basis: row.product_change_basis,
      url: row.source_url,
      searchable: [title.toLowerCase(), reason.toLowerCase()],
    };
  });
}

/** Every month of the release, 'YYYY-MM', from the first date to the collection cutoff. */
export function months(release) {
  const result = [];
  let [year, month] = release.first.split('-').map(Number);
  const last = release.cutoff.slice(0, 7);
  for (;;) {
    const key = `${year}-${String(month).padStart(2, '0')}`;
    if (key > last) return result;
    result.push(key);
    if (++month > 12) { month = 1; year++; }
  }
}

const years = release => {
  const result = [];
  for (let year = +release.first.slice(0, 4); year <= +release.cutoff.slice(0, 4); year++) result.push(year);
  return result;
};
const inMatchedPeriod = (record, release) => record.date.slice(5) <= release.cutoff.slice(5);

function matcher(filters, release) {
  const { type, service, facet } = filters;
  const q = (filters.q || '').toLowerCase();
  return record => record.date >= release.first && record.date <= release.cutoff
    && (!type || record.type === type)
    && (!service || record.services.includes(service))
    && (!facet || record.facets.includes(facet))
    && (!q || record.searchable[0].includes(q) || record.searchable[1].includes(q));
}

/** Distinct filter choices, derived from the records. */
export function choices(records) {
  const distinct = values => [...new Set(values)].filter(Boolean).sort();
  return {
    type: distinct(records.map(r => r.type)),
    service: distinct(records.flatMap(r => r.services)),
    facet: distinct(records.flatMap(r => r.facets)),
  };
}

const bump = (object, key) => { object[key] = (object[key] || 0) + 1; };

/**
 * Count the records that pass a filter set ({type, service, facet, q}, all optional).
 * Returns:
 *   total      all filtered announcements, including U and NA
 *   annual     {year: {level: n}} over the matched period
 *   years      [{year, matched, total, inScale, change}]; change is the in-scale matched total against the previous year, or null
 *   monthly    {'YYYY-MM': {level: n}} for every month of the release
 *   monthlyTotals {'YYYY-MM': n} all filtered announcements in the month, including U and NA; the share denominator
 *   breakdown  {type|service|facet: {tag: {year: {level: n}}}} over the matched period; tags overlap, so do not sum across tags
 */
export function summarize(records, filters, release) {
  const matches = matcher(filters, release);
  const annual = {}, monthly = {}, monthlyTotals = {}, breakdown = { type: {}, service: {}, facet: {} };
  const perYear = {};
  for (const year of years(release)) { annual[year] = {}; perYear[year] = { year, matched: 0, total: 0, inScale: 0, change: null }; }
  for (const month of months(release)) { monthly[month] = {}; monthlyTotals[month] = 0; }
  let total = 0;
  for (const record of records) {
    if (!matches(record)) continue;
    const year = record.date.slice(0, 4);
    total++;
    perYear[year].total++;
    bump(monthly[record.date.slice(0, 7)], record.level);
    monthlyTotals[record.date.slice(0, 7)]++;
    if (!inMatchedPeriod(record, release)) continue;
    perYear[year].matched++;
    if (record.level !== 'NA') perYear[year].inScale++;
    bump(annual[year], record.level);
    const tags = { type: record.type ? [record.type] : [], service: record.services, facet: record.facets };
    for (const key of Object.keys(tags)) for (const tag of tags[key]) {
      const byYear = (breakdown[key][tag] ??= {});
      bump((byYear[year] ??= {}), record.level);
    }
  }
  const list = Object.values(perYear);
  list.forEach((entry, i) => {
    const previous = list[i - 1];
    if (previous && previous.inScale) entry.change = entry.inScale / previous.inScale - 1;
  });
  return { total, annual, years: list, monthly, monthlyTotals, breakdown };
}

/**
 * Announcements per tag and year from one summary.breakdown[key], with every level counted together:
 * {tag: {year: n}}. Tags overlap for service and facet, so do not sum across tags.
 */
export function tagTotals(byTag) {
  const result = {};
  for (const [tag, byYear] of Object.entries(byTag)) {
    result[tag] = {};
    for (const [year, levels] of Object.entries(byYear)) result[tag][year] = Object.values(levels).reduce((sum, n) => sum + n, 0);
  }
  return result;
}

/**
 * The records behind a count, newest first. drill is optional:
 *   {month: 'YYYY-MM', level}  one month and level
 *   {year, level}              one year's matched period and level
 * level may be omitted to take every level.
 */
export function select(records, filters, release, drill = {}) {
  const matches = matcher(filters, release);
  const year = drill.year == null ? null : String(drill.year);
  return records.filter(record => matches(record)
    && (!drill.level || record.level === drill.level)
    && (!drill.month || record.date.startsWith(drill.month))
    && (!year || (record.date.startsWith(year) && inMatchedPeriod(record, release))))
    .sort((a, b) => (a.date < b.date) - (a.date > b.date) || (a.title > b.title) - (a.title < b.title) || (a.url > b.url) - (a.url < b.url));
}

/** A level's share of all filtered announcements in a period, in percent; null when the period is empty. */
export const sharePercent = (n, periodTotal) => periodTotal ? 100 * n / periodTotal : null;

const cell = value => /[",\r\n]/.test(value) ? '"' + value.replaceAll('"', '""') + '"' : value;

/** CSV text of records, with the nine public fields under their dataset names. */
export function toCsv(records) {
  const lines = records.map(r => [r.date, r.title, r.services.join('; '), r.type, r.facets.join('|'), r.level, r.reason, r.basis, r.url]
    .map(value => cell(value ?? '')).join(','));
  return [FIELDS.join(','), ...lines].join('\r\n') + '\r\n';
}

/**
 * Announcements, and those without a service tag ('unknown'), per year over the matched period, ignoring filters:
 * {year: {n, missing}}. Most early records have no tag, so one service's counts are not comparable across periods.
 */
export function untagged(records, release) {
  const result = {};
  for (const year of years(release)) result[year] = { n: 0, missing: 0 };
  for (const record of records) {
    if (record.date < release.first || record.date > release.cutoff || !inMatchedPeriod(record, release)) continue;
    const counts = result[record.date.slice(0, 4)];
    counts.n++;
    if (record.services.includes('unknown')) counts.missing++;
  }
  return result;
}
