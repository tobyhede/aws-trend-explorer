const magnitudeNames = {'1':'Parameter change','2':'Capability refinement','3':'New capability','4':'Major product expansion','5':'New product',U:'Needs review'};
const magnitudeKeys = Object.keys(magnitudeNames);

function magnitudeRecord(row) {
  if (!row.product_change_level) return '';
  const name = row.product_change_level === 'NA' ? 'Outside product-change scale' : levelLabel(row.product_change_level);
  return '<p><b>Magnitude level</b> · ' + esc(name)
    + (row.product_change_reason ? '<br>' + esc(row.product_change_reason) : '')
    + (row.product_change_basis ? '<br><b>Classification basis</b> · '+esc(row.product_change_basis) : '') + '</p>';
}

function drawMagnitude() {
  if (!data) return;
  const rows = data.magnitude || [];
  const totals = {2025: 0, 2026: 0};
  const yearCounts = {2025: {}, 2026: {}};
  const byScope = new Map();
  for (const {scope,rating,year,n} of rows) {
    totals[year] += n;
    yearCounts[year][rating] = (yearCounts[year][rating] || 0) + n;
    if (!byScope.has(scope)) byScope.set(scope, {});
    const group = byScope.get(scope);
    group[rating] = (group[rating] || 0) + n;
  }
  el('magnitudeCount').textContent = 'On the scale: ' + fmt(totals[2025]) + ' announcements in 2025 and ' + fmt(totals[2026]) + ' in 2026. Outside the scale: ' + (data.magnitude_excluded || []).map(r => r.year + ' — ' + fmt(r.n)).join(' · ') + '. All figures follow the selected filters.';
  if (!rows.length) {
    el('magnitudeYears').textContent = 'No announcements match the selected filters in the comparison periods.';
    el('magnitudeMatrix').replaceChildren();
    return;
  }
  const cell = (n,scope,rating,year) => n
    ? '<button data-scope="'+esc(scope)+'" data-rating="'+rating+'" data-year="'+year+'" aria-label="'
      +esc(scope ? scopeName(scope)+', ' : '')+esc(magnitudeNames[rating])+', '+(year||'both years')+', '+fmt(n)+' announcements">'+fmt(n)+'</button>'
    : '0';
  const scopes = [...byScope.keys()].sort((a,b)=>scopeName(a).localeCompare(scopeName(b)));
  const maximum = Math.max(...[...byScope.values()].flatMap(counts=>Object.values(counts)));
  const head = magnitudeKeys.map(k=>'<th scope="col">'+levelLabel(k)+'</th>').join('');
  const body = scopes.map(scope=>{
    const cells = magnitudeKeys.map(k=>{
      const n = byScope.get(scope)[k] || 0;
      return '<td style="background:color-mix(in srgb,var(--series) '+(n ? (6+34*n/maximum).toFixed(1) : 0)+'%,transparent)">'+cell(n,scope,k,'')+'</td>';
    }).join('');
    return '<tr><th scope="row">'+esc(scopeName(scope))+'</th>'+cells+'</tr>';
  }).join('');
  el('magnitudeMatrix').innerHTML = '<table class="bars"><thead><tr><th scope="col">Earlier scope</th>'+head+'</tr></thead><tbody>'+body+'</tbody></table>';
  const share = el('magnitudeUnit').value === 'share';
  const value = (year,k) => {
    const n = yearCounts[year][k] || 0;
    return share && totals[year] ? 100*n/totals[year] : n;
  };
  const maxValue = Math.max(1,...[2025,2026].flatMap(y=>magnitudeKeys.map(k=>value(y,k))));
  const signed = (n,digits) => (n > 0 ? '+' : n < 0 ? '−' : '') + (digits == null ? fmt(Math.abs(n)) : Math.abs(n).toFixed(digits));
  const chartRows = magnitudeKeys.map(k=>{
    const name = levelLabel(k);
    let bars = '';
    for (const year of [2025,2026]) {
      const n = yearCounts[year][k] || 0;
      const label = share ? (totals[year] ? value(year,k).toFixed(1)+'%' : '—') : fmt(n);
      const attributes = 'data-rating="'+k+'" data-scope="" data-year="'+year+'" aria-label="'+magnitudeNames[k]+', '+year+', '+fmt(n)+' announcements"';
      // Bars stop at 82% of the track so the value always fits beside the bar end.
      bars += '<button '+attributes+(n?'':' disabled')+'><span class="yr">'+year+'</span><span class="track"><i class="magBar year'+year+'" style="width:'+(82*value(year,k)/maxValue).toFixed(2)+'%"></i><b>'+label+'</b></span></button>';
    }
    const before = yearCounts[2025][k] || 0, after = yearCounts[2026][k] || 0;
    const change = share
      ? (totals[2025] && totals[2026] ? signed(value(2026,k)-value(2025,k),1)+' pts' : '—')
      : signed(after-before)+(before ? '<small>'+signed(100*(after/before-1),1)+'%</small>' : '');
    return '<tr><th scope="row">'+name+'</th><td class="magPair">'+bars+'</td><td class="chg">'+change+'</td></tr>';
  }).join('');
  el('magnitudeYears').innerHTML = '<table class="bars magYears"><thead><tr><th scope="col">Level</th><th scope="col" style="text-align:left">'+(share?'Share of in-scale announcements':'Announcements')+', January 1–October 28</th><th scope="col">Change</th></tr></thead><tbody>'+chartRows+'</tbody></table>';
  function drillMagnitude(event) {
    const button = event.target.closest('button[data-rating]');
    if (!button) return;
    const {scope,rating,year} = button.dataset;
    selectPeriod(year ? year+'-01-01' : '2025-01-01',year ? year+'-10-28' : '2026-10-28',scope,rating,true);
  }
  el('magnitudeMatrix').onclick = drillMagnitude;
  el('magnitudeYears').onclick = drillMagnitude;
}
