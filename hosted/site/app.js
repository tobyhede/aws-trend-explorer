// Page behaviour for the hosted explorer. All filtering and counting is in counting.js; this file only draws.
import { parquetReadObjects } from './vendor/hyparquet/index.js';
import { RELEASE, DATASET } from './release.js';
import { LEVELS, LEVEL_NAMES, PERIODS, periodOf, prepare, choices, months, summarize, select, sharePercent, tagTotals, toCsv, untagged } from './counting.js';

// serve.py marks the page when it runs from the release bundle, where saved announcement text can be read. The published site never has it.
const LOCAL = document.documentElement.hasAttribute('data-local');

const PAGE_SIZE = 25;
const el = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = n => n.toLocaleString('en-GB');
const pretty = tag => tag.replaceAll('_', ' ');
const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const longDate = iso => `${+iso.slice(8, 10)} ${MONTH_NAMES[+iso.slice(5, 7) - 1]} ${iso.slice(0, 4)}`;
const dayMonth = iso => `${+iso.slice(8, 10)} ${MONTH_NAMES[+iso.slice(5, 7) - 1]}`;
const monthName = month => `${MONTH_NAMES[+month.slice(5, 7) - 1]} ${month.slice(0, 4)}`;
const levelLabel = level => /\d/.test(level) ? `${level} · ${LEVEL_NAMES[level]}` : LEVEL_NAMES[level];

// The final month is partial when the collection cutoff is not that month's last day.
const lastMonth = RELEASE.cutoff.slice(0, 7);
const cutoffDay = +RELEASE.cutoff.slice(8, 10);
const finalMonthIsPartial = cutoffDay < new Date(Date.UTC(+lastMonth.slice(0, 4), +lastMonth.slice(5, 7), 0)).getUTCDate();
const partialNote = month => finalMonthIsPartial && month === lastMonth ? ` (partial month, to ${dayMonth(RELEASE.cutoff)})` : '';

let records = [];
let missingTags = {}; // {year: {n, missing}}: announcements without a service tag, ignoring filters
let summary = null;
let active = {};     // the filter set the current summary was counted with
let drill = {};      // {month, level} or {year, level}; empty when nothing is selected
let listed = [];
let offset = 0;
let drawnWidth = 0;  // the width the monthly chart was last drawn at
let chartFocus = null; // 'month|level' of the chart segment that holds the tab stop

const filters = () => Object.fromEntries(['q', 'type', 'service', 'facet'].map(key => [key, el(key).value]).filter(([, value]) => value));

// One shared tooltip. It repeats values that the tables and the marks' accessible names already give, so it is hidden from assistive technology.
const tip = document.createElement('div');
tip.className = 'tip';
tip.hidden = true;
tip.setAttribute('aria-hidden', 'true');
document.body.append(tip);
const hideTip = () => { tip.hidden = true; };

/** rows: [{value, label, level?, on?}]. Text goes in through textContent. */
function showTip(title, rows, x, y) {
  const head = document.createElement('p');
  head.textContent = title;
  tip.replaceChildren(head, ...rows.map(({ value, label, level, on }) => {
    const row = document.createElement('div'), key = document.createElement('i'), number = document.createElement('b'), name = document.createElement('span');
    if (on) row.className = 'on';
    if (level) key.className = 'swatch lv' + level;
    number.textContent = value;
    name.textContent = label;
    row.append(key, number, name);
    return row;
  }));
  tip.hidden = false;
  tip.style.left = Math.max(8, Math.min(x + 14, innerWidth - tip.offsetWidth - 8)) + 'px';
  tip.style.top = Math.max(8, Math.min(y + 14, innerHeight - tip.offsetHeight - 8)) + 'px';
}

const percent = (part, whole) => whole ? Math.round(100 * part / whole) + '%' : '—';
// Share of announcements without a service tag in a period's matched periods.
function periodMissing(period) {
  let n = 0, missing = 0;
  for (let year = period.first; year <= period.last; year++) if (missingTags[year]) { n += missingTags[year].n; missing += missingTags[year].missing; }
  return percent(missing, n);
}
const missingText = () => {
  const parts = PERIODS.map(p => `${periodMissing(p)} of ${p.label} announcements (${p.first}–${p.last})`);
  return `Service tags are missing on ${parts.slice(0, -1).join(', ')} and ${parts.at(-1)}`;
};
const NOT_COMPARABLE = "One service's counts are therefore not comparable across periods";

const seriesName = series => series === 'total' ? 'All announcements' : levelLabel(series);

// Small multiples: one panel per selected series, each on its own scale, because level 2 counts are about a hundred times level 5 counts.
function drawAnnualTrend() {
  const years = summary.years;
  const shown = Array.from(el('annualLegend').querySelectorAll('input:checked'), input => input.value);
  if (active.service) {
    el('annualTrends').textContent = `${missingText()}. ${NOT_COMPARABLE}, so the yearly panels are not drawn for a single service.`;
    return;
  }
  if (!shown.length) {
    el('annualTrends').textContent = 'Select a series to see its trend.';
    return;
  }
  const width = 240, height = 136, left = 36, right = 14, top = 20, bottom = 22;
  const plotWidth = width - left - right, plotHeight = height - top - bottom, band = plotWidth / Math.max(1, years.length - 1);
  el('annualTrends').innerHTML = shown.map(series => {
    const counts = years.map(y => series === 'total' ? y.matched : summary.annual[y.year][series] || 0);
    const ceiling = niceCeiling(Math.max(1, ...counts));
    const xs = years.map((_, i) => left + band * i), ys = counts.map(count => top + plotHeight * (1 - count / ceiling));
    const grid = [0, 0.5, 1].map(t => {
      const y = top + plotHeight * (1 - t);
      return `<line class="grid" x1="${left}" y1="${y}" x2="${width - right}" y2="${y}"/><text x="${left - 6}" y="${y + 3.5}" text-anchor="end">${fmt(ceiling * t)}</text>`;
    }).join('');
    // The middle period (COVID) is shaded; the key above the panels names all three.
    const periods = PERIODS.map((p, index) => {
      const first = years.findIndex(y => y.year === p.first), last = years.findLastIndex(y => y.year <= p.last);
      if (index % 2 === 0 || first < 0 || last < 0) return '';
      const x0 = first ? (xs[first] + xs[first - 1]) / 2 : left, x1 = last < years.length - 1 ? (xs[last] + xs[last + 1]) / 2 : width - right;
      return `<rect class="period" x="${x0.toFixed(2)}" y="${top}" width="${(x1 - x0).toFixed(2)}" height="${plotHeight}"/>`;
    }).join('');
    const labelled = new Set([years[0].year, PERIODS[1].first, years.at(-1).year]);
    const marks = years.map((y, i) => {
      const drillable = series !== 'total' && counts[i] ? ` data-level="${series}"` : '';
      const selected = drill.year === y.year && drill.level === series ? ' class="selected"' : '';
      return `<rect class="hit" data-series="${series}" data-year="${y.year}" data-count="${counts[i]}"${drillable} x="${(xs[i] - band / 2).toFixed(2)}" y="0" width="${band.toFixed(2)}" height="${height}"/><circle${selected} cx="${xs[i].toFixed(2)}" cy="${ys[i].toFixed(2)}" r="3"/>${labelled.has(y.year) ? `<text x="${xs[i].toFixed(2)}" y="${height - 6}" text-anchor="middle">${y.year}</text>` : ''}`;
    }).join('');
    const summaryText = `${seriesName(series)}, 1 January to ${dayMonth(RELEASE.cutoff)}: ` + years.map((y, i) => `${y.year} ${fmt(counts[i])}`).join(', ') + '. ' + PERIODS.map(p => `${p.label} period ${p.first}–${p.last}`).join(', ') + '.';
    return `<div class="panel"><h3>${esc(seriesName(series))}</h3><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(summaryText)}">${grid}${periods}
      <polyline points="${xs.map((x, i) => x.toFixed(2) + ',' + ys[i].toFixed(2)).join(' ')}"/>${marks}
      <text class="end" x="${width - right}" y="${Math.max(10, ys.at(-1) - 9).toFixed(2)}" text-anchor="end">${fmt(counts.at(-1))}</text></svg></div>`;
  }).join('');
}

// The two most recent years side by side, one row per in-scale level: the page's headline comparison.
function drawCompare() {
  const [before, after] = summary.years.slice(-2);
  const share = el('compareUnit').value === 'share';
  const levels = LEVELS.filter(level => level !== 'NA');
  const count = (y, level) => summary.annual[y.year][level] || 0;
  const value = (y, level) => share ? sharePercent(count(y, level), y.inScale) ?? 0 : count(y, level);
  const max = Math.max(1, ...levels.flatMap(level => [value(before, level), value(after, level)]));
  const signed = (n, digits) => (n > 0 ? '+' : n < 0 ? '−' : '') + (digits == null ? fmt(Math.abs(n)) : Math.abs(n).toFixed(digits));
  el('compareYears').textContent = `${before.year} against ${after.year}`;
  const rows = levels.map(level => {
    const bars = [before, after].map((y, i) => {
      const n = count(y, level);
      const label = share ? (y.inScale ? value(y, level).toFixed(1) + '%' : '—') : fmt(n);
      const pressed = drill.year === y.year && drill.level === level;
      // Bars stop at 82% of the track so the value always fits beside the bar end. Widths are set after insertion: the page's policy forbids inline styles.
      return `<button type="button" data-year="${y.year}" data-level="${level}" aria-pressed="${pressed}" aria-label="${y.year}, ${esc(LEVEL_NAMES[level])}: ${fmt(n)} announcements. List them."${n ? '' : ' disabled'}><span class="yr">${y.year}</span><span class="track"><i class="bar ${i ? 'curr' : 'prev'}" data-width="${(82 * value(y, level) / max).toFixed(2)}"></i><b>${label}</b></span></button>`;
    }).join('');
    const a = count(before, level), b = count(after, level);
    const change = share
      ? (before.inScale && after.inScale ? signed(value(after, level) - value(before, level), 1) + ' pts' : '—')
      : signed(b - a) + (a ? `<small>${signed(100 * (b / a - 1), 1)}%</small>` : '');
    return `<tr><th scope="row">${esc(levelLabel(level))}</th><td class="pair">${bars}</td><td class="chg">${change}</td></tr>`;
  }).join('');
  el('compare').innerHTML = `<div class="legend"><span><i class="swatch prev"></i>${before.year}</span><span><i class="swatch curr"></i>${after.year}</span></div>
    <table class="compare"><thead><tr><th scope="col">Level</th><th scope="col" class="left">${share ? 'Share of in-scale announcements' : 'Announcements'}, 1 January to ${dayMonth(RELEASE.cutoff)}</th><th scope="col">Change</th></tr></thead><tbody>${rows}</tbody></table>`;
  el('compare').querySelectorAll('i[data-width]').forEach(bar => { bar.style.width = bar.dataset.width + '%'; });
  el('compareNote').textContent = `On the scale: ${fmt(before.inScale)} announcements in ${before.year} and ${fmt(after.inScale)} in ${after.year}. Outside the scale: ${fmt(count(before, 'NA'))} and ${fmt(count(after, 'NA'))}. Shares include needs review. All figures follow the filters.`;
}

// The two most recent years by release type, facet or service. Selecting a group filters the whole page by it.
function drawBreakdown() {
  const key = el('split').value, [before, after] = summary.years.slice(-2);
  const totals = tagTotals(summary.breakdown[key]);
  let rows = Object.keys(totals).map(tag => ({ tag, a: totals[tag][before.year] || 0, b: totals[tag][after.year] || 0 }))
    .sort((x, y) => (y.a + y.b) - (x.a + x.b) || (x.tag > y.tag) - (x.tag < y.tag));
  if (key === 'service') rows = rows.filter(row => row.tag !== 'unknown').slice(0, 10);
  const max = Math.max(1, ...rows.flatMap(row => [row.a, row.b]));
  const signed = n => (n > 0 ? '+' : n < 0 ? '−' : '') + fmt(Math.abs(n));
  el('breakYears').textContent = `${before.year} against ${after.year}`;
  el('breakNote').textContent = {
    type: 'Each announcement has one release type. Select a group to filter the whole page by it.',
    facet: 'An enhancement can carry several facets, so these counts overlap and must not be added up. Select a facet to filter the whole page by it.',
    service: 'The ten most frequent named services across both years. An announcement counts once per service, so these counts overlap and must not be added up. Select a service to filter the whole page by it.',
  }[key] + ` Both years cover 1 January to ${dayMonth(RELEASE.cutoff)}.`;
  const line = (year, n, kind) => `<span class="line"><span class="yr">${year}</span><span class="track"><i class="bar ${kind}" data-width="${(82 * n / max).toFixed(2)}"></i><b>${fmt(n)}</b></span></span>`;
  el('breakdown').innerHTML = rows.length ? `<div class="legend"><span><i class="swatch prev"></i>${before.year}</span><span><i class="swatch curr"></i>${after.year}</span></div>
    <table class="compare"><thead><tr><th scope="col">Group</th><th scope="col" class="left">Announcements</th><th scope="col">Change</th></tr></thead><tbody>`
    + rows.map(row => `<tr><th scope="row"><button type="button" class="linklike" data-tag="${esc(row.tag)}">${esc(pretty(row.tag))}</button></th><td class="pair">${line(before.year, row.a, 'prev')}${line(after.year, row.b, 'curr')}</td><td class="chg">${signed(row.b - row.a)}</td></tr>`).join('')
    + '</tbody></table>' : 'No announcements match the filters in these two periods.';
  el('breakdown').querySelectorAll('i[data-width]').forEach(bar => { bar.style.width = bar.dataset.width + '%'; });
}

function drawAnnual() {
  drawCompare();
  drawAnnualTrend();
  const years = summary.years;
  const head = years.map(y => `<th scope="col"${PERIODS.some(p => p.first === y.year) && y !== years[0] ? ' class="period-start"' : ''}>${y.year}</th>`).join('');
  const periodHead = PERIODS.map(p => [p, years.filter(y => periodOf(y.year) === p).length]).filter(([, n]) => n)
    .map(([p, n]) => `<th scope="colgroup" colspan="${n}" class="period">${esc(p.label)} ${p.first}–${p.last}</th>`).join('');
  const rows = LEVELS.map(level => `<tr><th scope="row">${esc(levelLabel(level))}</th>` + years.map(y => {
    const n = summary.annual[y.year][level] || 0;
    if (!n) return '<td>0</td>';
    const pressed = drill.year === y.year && drill.level === level;
    return `<td><button type="button" data-year="${y.year}" data-level="${level}" aria-pressed="${pressed}" aria-label="${y.year}, ${esc(LEVEL_NAMES[level])}: ${fmt(n)} announcements. List them.">${fmt(n)}</button></td>`;
  }).join('') + '</tr>').join('');
  const change = y => y.change == null ? '—' : (y.change >= 0 ? '+' : '−') + Math.abs(y.change * 100).toFixed(1) + '%';
  el('annual').innerHTML = `<table><caption class="note">1 January to ${dayMonth(RELEASE.cutoff)} in each year.${active.service ? ' ' + esc(missingText()) + '.' : ''}</caption>
    <thead><tr><td></td>${periodHead}</tr><tr><th scope="col">Magnitude level</th>${head}</tr></thead><tbody>${rows}
    <tr class="sum"><th scope="row">In-scale total (levels 1–5 and needs review)</th>${years.map(y => `<td>${fmt(y.inScale)}</td>`).join('')}</tr>
    <tr><th scope="row">In-scale change on the previous year</th>${years.map(y => `<td>${change(y)}</td>`).join('')}</tr>
    <tr><th scope="row">All announcements in the matched period</th>${years.map(y => `<td>${fmt(y.matched)}</td>`).join('')}</tr>
    </tbody></table>`;
}

// The smallest axis maximum of at least n whose four gridlines fall on round numbers.
function niceCeiling(n) {
  for (let scale = 1; ; scale *= 10) for (const step of [1, 2, 2.5, 5]) if (4 * step * scale >= n && Number.isInteger(step * scale)) return 4 * step * scale;
}

function drawMonthly() {
  const share = el('unit').value === 'share';
  const all = months(RELEASE);
  const totals = all.map(month => summary.monthlyTotals[month]);
  const max = share ? 100 : niceCeiling(Math.max(1, ...totals));
  const width = Math.max(560, el('monthly').clientWidth || 1120), left = 48, right = 16, top = 16, height = 235, step = (width - left - right) / all.length;
  drawnWidth = el('monthly').clientWidth;
  const range = `${monthName(all[0])} to ${longDate(RELEASE.cutoff)}`;
  let svg = `<svg class="chart" viewBox="0 0 ${width} 300" role="group" aria-label="Monthly announcements by magnitude level, ${range}. ${share ? 'Share of all filtered announcements' : 'Counts'}. Arrow keys move between segments.">`;
  for (let tick = 0; tick <= 4; tick++) {
    const y = top + height - height * tick / 4;
    svg += `<line class="grid" x1="${left}" y1="${y}" x2="${width - right}" y2="${y}"/><text x="${left - 6}" y="${y + 4}" text-anchor="end">${fmt(Math.round(max * tick / 4))}${share ? '%' : ''}</text>`;
  }
  all.forEach((month, index) => {
    let bottom = top + height;
    const x = left + step * index;
    svg += `<rect class="col" data-month="${month}" x="${x.toFixed(2)}" y="${top}" width="${step.toFixed(2)}" height="${height}"/>`;
    LEVELS.forEach(level => {
      const n = summary.monthly[month][level] || 0;
      if (!n) return;
      const percent = sharePercent(n, totals[index]);
      const h = height * (share ? percent : n) / max;
      bottom -= h;
      const selected = drill.month === month && drill.level === level;
      const label = `${monthName(month)}${partialNote(month)}, ${LEVEL_NAMES[level]}: ${fmt(n)} announcements, ${percent.toFixed(1)}% of the month`;
      svg += `<rect class="seg lv${level}${selected ? ' selected' : ''}" tabindex="-1" role="button" data-month="${month}" data-level="${level}" x="${x.toFixed(2)}" y="${bottom.toFixed(2)}" width="${Math.max(1, step - 2).toFixed(2)}" height="${h.toFixed(2)}" aria-label="${esc(label)}. List them."><title>${esc(label)}</title></rect>`;
    });
    if (month.endsWith('-01') && (step >= 4 || PERIODS.some(p => p.first === +month.slice(0, 4)) || index === 0)) svg += `<text x="${x}" y="${top + height + 18}">${month.slice(0, 4)}</text>`;
    const starts = PERIODS.find(p => month === `${p.first}-01`);
    if (starts && index) svg += `<line class="period" x1="${x.toFixed(2)}" y1="${top}" x2="${x.toFixed(2)}" y2="${top + height}"/><text class="period" x="${(x + 4).toFixed(2)}" y="${top + 11}">${esc(starts.label)}</text>`;
    else if (starts) svg += `<text class="period" x="${(x + 4).toFixed(2)}" y="${top + 11}">${esc(starts.label)}</text>`;
    if (partialNote(month)) svg += `<rect class="partial" x="${(x - 2).toFixed(2)}" y="${top}" width="${(step + 2).toFixed(2)}" height="${height + 2}"/>`;
  });
  if (finalMonthIsPartial) svg += `<text x="${width - right}" y="291" text-anchor="end">Dashed outline: ${monthName(lastMonth)} is partial and ends on ${dayMonth(RELEASE.cutoff)}</text>`;
  el('monthly').innerHTML = svg + '</svg>';
  const segments = [...el('monthly').querySelectorAll('rect.seg')];
  const holder = segments.find(s => s.dataset.month + '|' + s.dataset.level === chartFocus) || segments[0];
  if (holder) holder.tabIndex = 0;

  el('monthlyTable').innerHTML = '<table><thead><tr><th scope="col">Month</th>' + LEVELS.map(level => `<th scope="col">${esc(LEVEL_NAMES[level])}</th>`).join('') + '<th scope="col">All</th></tr></thead><tbody>'
    + all.map((month, index) => `<tr><th scope="row">${month}${esc(partialNote(month))}</th>` + LEVELS.map(level => {
      const n = summary.monthly[month][level] || 0;
      const text = share ? (totals[index] ? sharePercent(n, totals[index]).toFixed(1) + '%' : '—') : fmt(n);
      if (!n) return `<td>${text}</td>`;
      const pressed = drill.month === month && drill.level === level;
      return `<td><button type="button" data-month="${month}" data-level="${level}" aria-pressed="${pressed}" aria-label="${monthName(month)}, ${esc(LEVEL_NAMES[level])}: ${fmt(n)} announcements. List them.">${text}</button></td>`;
    }).join('') + `<td>${fmt(totals[index])}</td></tr>`).join('') + '</tbody></table>';
}

// Every level and the total for one month; the level under the pointer or focus is marked.
function monthTip(month, level, x, y) {
  const total = summary.monthlyTotals[month];
  const rows = LEVELS.map(l => {
    const n = summary.monthly[month][l] || 0;
    return { level: l, value: fmt(n), label: `${LEVEL_NAMES[l]}${total ? ' · ' + sharePercent(n, total).toFixed(1) + '%' : ''}`, on: l === level };
  });
  showTip(monthName(month) + partialNote(month), [...rows, { value: fmt(total), label: 'All announcements' }], x, y);
}

// One tab stop for the whole chart; arrow keys move between segments.
function moveChartFocus(from, key) {
  const all = months(RELEASE);
  const at = (month, level) => el('monthly').querySelector(`rect.seg[data-month="${month}"][data-level="${level}"]`);
  let monthIndex = all.indexOf(from.dataset.month), levelIndex = LEVELS.indexOf(from.dataset.level), target = null;
  if (key === 'ArrowUp' || key === 'ArrowDown') {
    for (let i = levelIndex + (key === 'ArrowUp' ? 1 : -1); i >= 0 && i < LEVELS.length && !target; i += key === 'ArrowUp' ? 1 : -1) target = at(all[monthIndex], LEVELS[i]);
  } else {
    for (let m = monthIndex + (key === 'ArrowRight' ? 1 : -1); m >= 0 && m < all.length && !target; m += key === 'ArrowRight' ? 1 : -1) {
      target = at(all[m], LEVELS[levelIndex]) || el('monthly').querySelector(`rect.seg[data-month="${all[m]}"]`);
    }
  }
  if (!target) return;
  from.tabIndex = -1;
  target.tabIndex = 0;
  target.focus();
  chartFocus = target.dataset.month + '|' + target.dataset.level;
}

const drillText = () => `${LEVEL_NAMES[drill.level]} · ${drill.month ? monthName(drill.month) + partialNote(drill.month) : `1 January to ${dayMonth(RELEASE.cutoff)} ${drill.year}`}`;
const FILTER_NAMES = { q: 'Search', type: 'Release type', service: 'Service', facet: 'Enhancement facet' };

// The sticky bar under the filters: every active filter and the selected count, each removable.
function drawState() {
  const chips = Object.entries(active).map(([key, value]) => `<button type="button" data-clear="${key}" aria-label="Remove filter. ${FILTER_NAMES[key]}">${FILTER_NAMES[key]}: ${esc(key === 'q' ? `“${value}”` : pretty(value))} ×</button>`);
  if (drill.level) chips.push(`<button type="button" data-clear="drill" aria-label="Clear the selected count">Listing: ${esc(drillText())} ×</button><a href="#recordsTitle">Go to the list</a>`);
  el('state').innerHTML = chips.length ? '<span>Active</span>' + chips.join('') : '';
  for (const key of Object.keys(FILTER_NAMES)) el(key).classList.toggle('on', Boolean(active[key]));
}

function describeSelection() {
  drawState();
  const labels = Object.entries(active).map(([key, value]) => key === 'q' ? `search “${value}”` : `${{ type: 'release type', service: 'service', facet: 'facet' }[key]} ${pretty(value)}`);
  let text = fmt(listed.length) + (listed.length === 1 ? ' record' : ' records');
  if (drill.level) text += ` · ${drillText()}`;
  if (labels.length) text += ' · ' + labels.join(', ');
  el('selection').innerHTML = esc(text) + (drill.level ? ' <button type="button" class="linklike" id="clearSelection">Show all filtered records</button>' : '');
}

function drawRecords() {
  const page = listed.slice(offset, offset + PAGE_SIZE);
  el('records').innerHTML = page.map(r => `<li><time datetime="${r.date}">${r.date}</time>
    <span class="title"><a href="${esc(r.url)}" rel="noreferrer">${esc(r.title)}</a></span>
    <p><span class="level">${esc(levelLabel(r.level))}</span>${esc(r.reason)}</p>
    <p class="meta">${esc(r.services.join(', '))} · ${esc(pretty(r.type ?? ''))}${r.facets.length ? ' · ' + esc(r.facets.map(pretty).join(', ')) : ''}</p>
    ${LOCAL ? `<details class="saved" data-url="${esc(r.url)}"><summary>Saved announcement text</summary><p></p></details>` : ''}</li>`).join('');
  el('page').textContent = listed.length ? `${fmt(offset + 1)}–${fmt(offset + page.length)} of ${fmt(listed.length)}` : 'No matching records';
  el('previous').disabled = offset === 0;
  el('next').disabled = offset + PAGE_SIZE >= listed.length;
  el('export').disabled = !listed.length;
}

function list() {
  // Uses the summary's own filter set, so a count selected while a search is still being typed lists exactly that count.
  listed = select(records, active, RELEASE, drill);
  offset = 0;
  describeSelection();
  drawRecords();
}

// Recount everything for the current filters. Changing a filter clears the selected count.
function refresh() {
  drill = {};
  active = filters();
  summary = summarize(records, active, RELEASE);
  el('total').innerHTML = `<strong>${fmt(summary.total)}</strong> of ${fmt(records.length)} announcements match the filters.` + (active.service ? ` ${esc(missingText())}. ${esc(NOT_COMPARABLE)}.` : '');
  drawAnnual();
  drawMonthly();
  drawBreakdown();
  list();
}

function choose(target) {
  const { month, year, level } = target.dataset;
  hideTip();
  drill = month ? { month, level } : { year: +year, level };
  if (month) chartFocus = month + '|' + level;
  drawAnnual();
  drawMonthly();
  list();
  el('recordsTitle').scrollIntoView({ behavior: 'smooth' });
  el('recordsTitle').focus({ preventScroll: true });
}

function exportCsv() {
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([toCsv(listed)], { type: 'text/csv;charset=utf-8' }));
  link.download = `aws-announcements-${RELEASE.date}-selection.csv`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

function wire() {
  const names = { type: 'All release types', service: 'All services', facet: 'All facets' };
  const options = choices(records);
  for (const key of Object.keys(names)) {
    el(key).add(new Option(names[key], ''));
    for (const value of options[key]) el(key).add(new Option(pretty(value), value));
    el(key).onchange = refresh;
  }
  let timer;
  el('q').oninput = () => { clearTimeout(timer); timer = setTimeout(refresh, 200); };
  el('filters').onsubmit = event => { event.preventDefault(); refresh(); };
  el('filters').onreset = () => setTimeout(refresh);
  el('annualLegend').innerHTML = [...LEVELS, 'total'].map(series =>
    `<label><input type="checkbox" value="${series}" ${series === 'total' ? '' : 'checked'}>${esc(seriesName(series))}</label>`
  ).join('');
  el('annualLegend').onchange = drawAnnualTrend;
  el('periodKey').textContent = `Shaded: the ${PERIODS[1].label} period, ${PERIODS[1].first}–${PERIODS[1].last}. Before it, the ${PERIODS[0].label} period (${PERIODS[0].first}–${PERIODS[0].last}); after it, the ${PERIODS[2].label} period (${PERIODS[2].first}–${PERIODS[2].last}).`;
  // The site stores nothing in the browser, so a theme choice lasts until the page is reloaded.
  el('theme').onchange = () => { document.documentElement.dataset.theme = el('theme').value; };
  el('split').onchange = drawBreakdown;
  el('breakdown').onclick = event => {
    const button = event.target.closest('button[data-tag]');
    if (!button) return;
    el(el('split').value).value = button.dataset.tag;
    refresh();
    el('filters').scrollIntoView({ behavior: 'smooth' });
  };
  // Saved announcement text is read from serve.py one record at a time, and only in the release bundle.
  el('records').addEventListener('toggle', async event => {
    const box = event.target;
    if (!box.matches('details.saved') || !box.open || box.dataset.loaded) return;
    box.dataset.loaded = '1';
    const response = await fetch('api/text?url=' + encodeURIComponent(box.dataset.url));
    box.querySelector('p').textContent = response.ok ? (await response.json()).text || 'No saved text for this announcement.' : 'The saved text could not be read.';
  }, true);
  el('compareUnit').onchange = drawCompare;
  el('compare').onclick = event => { const button = event.target.closest('button[data-level]'); if (button) choose(button); };
  el('state').onclick = event => {
    const chip = event.target.closest('[data-clear]');
    if (!chip) return;
    if (chip.dataset.clear === 'drill') { drill = {}; drawAnnual(); drawMonthly(); list(); }
    else { el(chip.dataset.clear).value = ''; refresh(); }
  };
  el('unit').onchange = drawMonthly;
  el('annual').onclick = event => { const button = event.target.closest('button[data-level]'); if (button) choose(button); };
  el('annualTrends').onclick = event => { const hit = event.target.closest('rect.hit[data-level]'); if (hit) choose(hit); };
  el('annualTrends').onpointermove = event => {
    const hit = event.target.closest('rect.hit');
    if (!hit) return hideTip();
    const { series, year, count } = hit.dataset;
    showTip(`${seriesName(series)} · ${year}`, [{ value: fmt(+count), label: `announcements, 1 January to ${dayMonth(RELEASE.cutoff)}` }], event.clientX, event.clientY);
  };
  el('annualTrends').onpointerleave = hideTip;
  el('monthlyTable').onclick = event => { const button = event.target.closest('button[data-level]'); if (button) choose(button); };
  el('monthly').onpointermove = event => {
    const mark = event.target.closest('[data-month]');
    if (mark) monthTip(mark.dataset.month, mark.dataset.level, event.clientX, event.clientY); else hideTip();
  };
  el('monthly').onpointerleave = hideTip;
  el('monthly').addEventListener('focusin', event => {
    const segment = event.target.closest('rect.seg');
    if (!segment) return;
    const box = segment.getBoundingClientRect();
    monthTip(segment.dataset.month, segment.dataset.level, box.right, box.top);
  });
  el('monthly').addEventListener('focusout', hideTip);
  new ResizeObserver(() => { if (summary && el('monthly').clientWidth !== drawnWidth) drawMonthly(); }).observe(el('monthly'));
  el('monthly').onclick = event => { const segment = event.target.closest('rect.seg'); if (segment) choose(segment); };
  el('monthly').onkeydown = event => {
    const segment = event.target.closest('rect.seg');
    if (!segment) return;
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(segment); }
    else if (event.key.startsWith('Arrow')) { event.preventDefault(); moveChartFocus(segment, event.key); }
  };
  el('selection').onclick = event => { if (event.target.id === 'clearSelection') { drill = {}; drawAnnual(); drawMonthly(); list(); } };
  el('previous').onclick = () => { offset = Math.max(0, offset - PAGE_SIZE); drawRecords(); el('recordsTitle').focus(); };
  el('next').onclick = () => { offset += PAGE_SIZE; drawRecords(); el('recordsTitle').focus(); };
  el('export').onclick = exportCsv;
}

function showRelease() {
  document.querySelectorAll('[data-release]').forEach(node => { node.textContent = longDate(RELEASE.date); });
  document.querySelectorAll('[data-cutoff]').forEach(node => { node.textContent = longDate(RELEASE.cutoff); });
  document.querySelectorAll('[data-cutoff-day]').forEach(node => { node.textContent = dayMonth(RELEASE.cutoff); });
  el('download').href = DATASET;
  el('legend').innerHTML = LEVELS.map(level => `<span><i class="swatch lv${level}"></i>${esc(levelLabel(level))}</span>`).join('');
}

async function start() {
  showRelease();
  const response = await fetch(DATASET);
  if (!response.ok) throw new Error(`The public dataset could not be loaded (${response.status}).`);
  records = prepare(await parquetReadObjects({ file: await response.arrayBuffer() }));
  missingTags = untagged(records, RELEASE);
  el('coverage').textContent = `${fmt(records.length)} announcements, ${longDate(RELEASE.first)} to ${longDate(RELEASE.cutoff)}. Release ${longDate(RELEASE.date)}.`;
  wire();
  refresh();
}

start().catch(error => {
  el('coverage').textContent = '';
  el('error').textContent = (location.protocol === 'file:' ? 'Open this page through a web server, not as a file. ' : '') + error.message;
});
