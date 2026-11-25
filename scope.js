const scopeStyles = {
  new_product: ['New product', '#653f79'],
  new_capability: ['New capability', '#086c67'],
  improved: ['Existing capability improved', '#ba652c'],
  extended: ['Existing capability extended', '#507baf'],
  operational: ['Commercial, lifecycle or maintenance', '#845c47'],
  unclear: ['Unclear', '#85908e']
};
const scopeName = key => scopeStyles[key]?.[0] ?? key;
const signedCount = value => (value > 0 ? '+' : '') + fmt(value);

function drawScope() {
  const scopes = el('scope').value ? [el('scope').value] : Object.keys(scopeStyles);
  const months = new Map();
  for (let year = 2025; year <= 2026; year++) {
    for (let month = 1; month <= (year === 2025 ? 12 : 10); month++) {
      months.set(year + '-' + String(month).padStart(2, '0') + '-01', {});
    }
  }
  for (const row of data.scope_months) months.get(row.date)[row.scope] = row.count;
  drawScopeMonths(months, scopes);
  drawScopeChange(scopes);
}

function drawScopeMonths(months, scopes) {
  const share = el('scopeUnit').value === 'share';
  const total = counts => scopes.reduce((sum, scope) => sum + (counts[scope] || 0), 0);
  const maximum = share ? 100 : Math.max(1, ...Array.from(months.values(), total));
  const left = 46, baseline = 182, height = 154, step = 35;
  let chart = '', table = '';
  for (let tick = 0; tick <= 4; tick++) {
    const y = baseline - tick * height / 4;
    chart += '<path d="M'+left+' '+y+'h'+(step*months.size)+'" stroke="#e0e9e4"/>'
      + text(left-6,y+4,Math.round(maximum*tick/4)+(share?'%':''),'end');
  }
  let i = 0;
  for (const [date, counts] of months) {
    let y = baseline;
    const x = left + i*step + 4, sum = total(counts);
    table += '<tr><th>'+date.slice(0,7)+'</th>';
    for (const scope of scopes) {
      const n = counts[scope] || 0;
      table += '<td>' + (n ? '<button data-month="'+date+'" data-label="'+scope+'">'+fmt(n)+'</button>' : '0') + '</td>';
      if (!n) continue;
      const fraction = n / sum, size = height*(share ? fraction : n/maximum);
      y -= size;
      const description = date.slice(0,7)+' · '+scopeName(scope)+' · '+fmt(n)+' ('+(100*fraction).toFixed(1)+'%)';
      chart += '<rect class="point" role="button" tabindex="0" data-month="'+date+'" data-label="'+scope
        +'" x="'+x+'" y="'+y+'" width="26" height="'+size+'" fill="'+scopeStyles[scope][1]+'" aria-label="'+description+'"><title>'+description+'</title></rect>';
    }
    table += '</tr>';
    if (i % 3 === 0) chart += text(x+13,baseline+18,date.slice(0,7));
    i++;
  }
  plot('scopeChart',chart,left+step*months.size+12,209,'Monthly announcements by primary scope');
  el('scopeLegend').innerHTML = scopes.map(key => '<span><i style="background:'+scopeStyles[key][1]+'"></i>'+scopeName(key)+'</span>').join('');
  el('scopeTable').innerHTML = '<table class="bars"><thead><tr><th>Month</th>'+scopes.map(key => '<th>'+scopeName(key)+'</th>').join('')+'</tr></thead><tbody>'+table+'</tbody></table>';
  const show = target => {
    const segment = target.closest('[data-month]');
    if (segment) selectPeriod(...interval({date:segment.dataset.month},'monthly'),segment.dataset.label);
  };
  el('scopeChart').onclick = event => show(event.target);
  el('scopeChart').onkeydown = event => {
    if (['Enter',' '].includes(event.key)) {event.preventDefault(); show(event.target);}
  };
  el('scopeTable').onclick = event => show(event.target);
}

function drawScopeChange(scopes) {
  const byScope = new Map(data.scope_delta.map(row => [row.scope,row]));
  const rows = scopes.map(scope => byScope.get(scope) || {scope,previous:0,current:0})
    .map(row => ({...row,delta:row.current-row.previous})).sort((a,b) => b.delta-a.delta);
  const limit = Math.max(1, ...rows.map(row => Math.abs(row.delta)));
  const net = rows.reduce((sum,row) => sum+row.delta,0);
  el('scopeNet').textContent = 'January 1–October 28 in both years. Net change: '+signedCount(net)+' announcements. Select a year’s count to inspect it or a scope name for its 13-week velocity.';
  const body = rows.map(({scope,current,previous,delta}) => {
    const width = 50*Math.abs(delta)/limit;
    const bar = '<i style="width:'+width+'%;left:'+(delta<0 ? 50-width : 50)+'%;background:'+scopeStyles[scope][1]+'"></i>';
    const count = (n,year) => '<td><button data-label="'+scope+'" data-year="'+year+'">'+fmt(n)+'</button></td>';
    return '<tr><td><button data-label="'+scope+'">'+scopeName(scope)+'</button></td>'+count(previous,2025)+count(current,2026)
      +'<td class="delta-track">'+bar+'</td><td>'+signedCount(delta)+'</td></tr>';
  }).join('');
  el('scopeDelta').innerHTML = '<table class="bars"><thead><tr><th>Primary scope</th><th>2025</th><th>2026</th><th aria-label="Change around zero"></th><th>Change</th></tr></thead><tbody>'+body+'</tbody></table>';
  el('scopeDelta').onclick = event => {
    const button = event.target.closest('[data-label]');
    if (!button) return;
    const {label,year} = button.dataset;
    if (year) return selectPeriod(year+'-01-01',year+'-10-28',label);
    el('scope').value = label;
    el('measure').value = 'rolling';
    refresh().then(() => el('trend').scrollIntoView({behavior:'smooth',block:'center'}));
  };
}
