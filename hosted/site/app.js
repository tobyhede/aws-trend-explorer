// Page behaviour for the hosted explorer. All filtering and counting is in counting.js; this file only draws.
import { parquetReadObjects } from './vendor/hyparquet/index.js';
import { RELEASE, DATASET } from './release.js';
import { LEVELS, LEVEL_NAMES, prepare, choices, months, summarize, select, sharePercent, toCsv } from './counting.js';

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
let summary = null;
let active = {};     // the filter set the current summary was counted with
let drill = {};      // {month, level} or {year, level}; empty when nothing is selected
let listed = [];
let offset = 0;
let chartFocus = null; // 'month|level' of the chart segment that holds the tab stop

const filters = () => Object.fromEntries(['q', 'type', 'service', 'facet'].map(key => [key, el(key).value]).filter(([, value]) => value));

function drawAnnualTrend() {
  const years = summary.years;
  const series = Array.from(el('annualLegend').querySelectorAll('input:checked'), input => ({
    level: input.value,
    counts: years.map(y => input.value === 'total' ? y.matched : summary.annual[y.year][input.value] || 0)
  }));
  if (!series.length) {
    el('annualTrends').textContent = 'Select a series to see its trend.';
    return;
  }
  const ceiling = niceCeiling(Math.max(...series.flatMap(s => s.counts)));
  const lines = series.map(({level, counts}) => {
    const points = counts.map((count, i) => [100 * i / Math.max(1, years.length - 1), 100 * (1 - count / ceiling)]);
    return `<polyline class="lv${level}" points="${points.map(p => p.join(',')).join(' ')}"><title>${esc(LEVEL_NAMES[level] || 'All announcements')}</title></polyline>`;
  }).join('');
  const ticks = [4, 3, 2, 1, 0];
  el('annualTrends').innerHTML = `<div class="trend-scale">${ticks.map(t => `<span>${fmt(t * ceiling / 4)}</span>`).join('')}</div>
    <div class="trend-plot"><svg class="annual-lines" viewBox="0 0 100 100" preserveAspectRatio="none">
      <path class="trend-grid" d="${ticks.map(t => `M0 ${25*t}H100`).join(' ')}"/>${lines}</svg>
    <div class="trend-years">${years.map(y => `<span>${y.year}</span>`).join('')}</div></div>`;
}

function drawAnnual() {
  drawAnnualTrend();
  const years = summary.years;
  const head = years.map(y => `<th scope="col">${y.year}</th>`).join('');
  const rows = LEVELS.map(level => `<tr><th scope="row">${esc(levelLabel(level))}</th>` + years.map(y => {
    const n = summary.annual[y.year][level] || 0;
    if (!n) return '<td>0</td>';
    const pressed = drill.year === y.year && drill.level === level;
    return `<td><button type="button" data-year="${y.year}" data-level="${level}" aria-pressed="${pressed}" aria-label="${y.year}, ${esc(LEVEL_NAMES[level])}: ${fmt(n)} announcements. List them.">${fmt(n)}</button></td>`;
  }).join('') + '</tr>').join('');
  const change = y => y.change == null ? '—' : (y.change >= 0 ? '+' : '−') + Math.abs(y.change * 100).toFixed(1) + '%';
  el('annual').innerHTML = `<table><caption class="note">1 January to ${dayMonth(RELEASE.cutoff)} in each year</caption>
    <thead><tr><th scope="col">Magnitude level</th>${head}</tr></thead><tbody>${rows}
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
  const width = 1120, left = 48, right = 16, top = 16, height = 235, step = (width - left - right) / all.length;
  const range = `${monthName(all[0])} to ${longDate(RELEASE.cutoff)}`;
  let svg = `<svg class="chart" viewBox="0 0 ${width} 300" role="group" aria-label="Monthly announcements by magnitude level, ${range}. ${share ? 'Share of all filtered announcements' : 'Counts'}. Arrow keys move between segments.">`;
  for (let tick = 0; tick <= 4; tick++) {
    const y = top + height - height * tick / 4;
    svg += `<line class="grid" x1="${left}" y1="${y}" x2="${width - right}" y2="${y}"/><text x="${left - 6}" y="${y + 4}" text-anchor="end">${Math.round(max * tick / 4)}${share ? '%' : ''}</text>`;
  }
  all.forEach((month, index) => {
    let bottom = top + height;
    const x = left + step * index;
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
    if (month.endsWith('-01')) svg += `<text x="${x}" y="${top + height + 18}">${month.slice(0, 4)}</text>`;
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
      return `<td>${share ? (totals[index] ? sharePercent(n, totals[index]).toFixed(1) + '%' : '—') : fmt(n)}</td>`;
    }).join('') + `<td>${fmt(totals[index])}</td></tr>`).join('') + '</tbody></table>';
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

function describeSelection() {
  const labels = Object.entries(active).map(([key, value]) => key === 'q' ? `search “${value}”` : `${{ type: 'release type', service: 'service', facet: 'facet' }[key]} ${pretty(value)}`);
  let text = fmt(listed.length) + (listed.length === 1 ? ' record' : ' records');
  if (drill.level) {
    const period = drill.month ? monthName(drill.month) + partialNote(drill.month) : `1 January to ${dayMonth(RELEASE.cutoff)} ${drill.year}`;
    text += ` · ${LEVEL_NAMES[drill.level]} · ${period}`;
  }
  if (labels.length) text += ' · ' + labels.join(', ');
  el('selection').innerHTML = esc(text) + (drill.level ? ' <button type="button" class="linklike" id="clearSelection">Show all filtered records</button>' : '');
}

function drawRecords() {
  const page = listed.slice(offset, offset + PAGE_SIZE);
  el('records').innerHTML = page.map(r => `<li><time datetime="${r.date}">${r.date}</time>
    <span class="title"><a href="${esc(r.url)}" rel="noreferrer">${esc(r.title)}</a></span>
    <p><span class="level">${esc(levelLabel(r.level))}</span>${esc(r.reason)}</p>
    <p class="meta">${esc(r.services.join(', '))} · ${esc(pretty(r.type ?? ''))}${r.facets.length ? ' · ' + esc(r.facets.map(pretty).join(', ')) : ''}</p></li>`).join('');
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
  el('total').innerHTML = `<strong>${fmt(summary.total)}</strong> of ${fmt(records.length)} announcements match the filters.`;
  drawAnnual();
  drawMonthly();
  list();
}

function choose(target) {
  const { month, year, level } = target.dataset;
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
  el('annualLegend').innerHTML = [...LEVELS, 'total'].map(level =>
    `<label><input type="checkbox" value="${level}" ${level === 'total' ? '' : 'checked'}><i class="swatch lv${level}"></i>${level === 'total' ? 'All announcements' : esc(levelLabel(level))}</label>`
  ).join('');
  el('annualLegend').onchange = drawAnnualTrend;
  el('unit').onchange = drawMonthly;
  el('annual').onclick = event => { const button = event.target.closest('button[data-level]'); if (button) choose(button); };
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
  el('coverage').textContent = `${fmt(records.length)} announcements, ${longDate(RELEASE.first)} to ${longDate(RELEASE.cutoff)}. Release ${longDate(RELEASE.date)}.`;
  wire();
  refresh();
}

start().catch(error => {
  el('coverage').textContent = '';
  el('error').textContent = (location.protocol === 'file:' ? 'Open this page through a web server, not as a file. ' : '') + error.message;
});
