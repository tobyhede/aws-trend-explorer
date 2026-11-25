(() => {
  const get = id => document.getElementById(id);
  const percent = value => value.toFixed(1) + '%';
  const count = value => Math.round(value).toLocaleString('en-US');
  const signed = (value, places) =>
    (value > 0 ? '+' : value < 0 ? '−' : '') + Math.abs(value).toFixed(places);
  const range = (values, format) => values.map(format).join(' to ');

  function sharePlot(years) {
    const maxShare = Math.max(5, ...years.flatMap(
      row => [row.observed_share, row.adjusted_share, row.share_interval[1]]
    ));
    const tick = Math.ceil(maxShare / 5);
    const ceiling = tick * 5;
    const x = value => 70 + 498 * value / ceiling;
    const shape = [];
    for (let i = 0; i <= 5; i++) {
      const value = i * tick;
      shape.push('<path d="M'+x(value)+' 23v89" stroke="#dbe3df"/>',
        '<text x="'+x(value)+'" y="135" class="axis" text-anchor="middle">'+value+'%</text>');
    }
    years.forEach((row, i) => {
      const y = 46 + i * 49;
      const [lo, hi] = row.share_interval;
      const observed = x(row.observed_share);
      shape.push('<text x="8" y="'+(y+3)+'" class="axis">'+row.year+'</text>',
        '<path d="M'+x(lo)+' '+(y+4)+'H'+x(hi)+' M'+x(lo)+' '+(y-2)+'v12 M'+x(hi)+' '+(y-2)+'v12" stroke="#086c67" stroke-width="2"/>',
        '<circle cx="'+x(row.adjusted_share)+'" cy="'+(y+4)+'" r="5" fill="#086c67"/>',
        '<path d="M'+observed+' '+(y-13)+'l4 4-4 4-4-4z" fill="#aa5034"/>');
    });
    return '<svg viewBox="0 0 600 150" style="width:100%;max-width:740px" role="img" aria-label="Annual shares of enhancements classified as architecture changes. Numeric values are in the annual table.">'+shape.join('')+'</svg>';
  }

  function render(result) {
    const {years, difference} = result;
    const [lo, hi] = difference.share_interval;
    const direction = lo <= 0 && hi >= 0
      ? 'The direction of the change in share is inconclusive.'
      : lo > 0 ? 'The adjusted share increased.' : 'The adjusted share decreased.';
    get('architectureStatus').textContent = direction;
    get('architecturePlot').innerHTML = sharePlot(years) +
      '<p><span style="color:#aa5034">◆</span> Observed share　<span style="color:#086c67">●</span> Audit-adjusted share with 95% range</p>';
    const pp = value => signed(value, 1);
    const n = value => signed(value, 0);
    get('architectureChange').textContent =
      'Adjusted change from 2025 to 2026 was ' + pp(difference.share_pp) +
      ' percentage points (95% range ' + range(difference.share_interval, pp) +
      '), or ' + n(difference.count) + ' announcements (95% range ' +
      range(difference.count_interval, n) + ').';
    get('architectureTable').innerHTML = '<table class="bars"><thead><tr><th>Year</th><th>Enhancements</th><th>Observed count</th><th>Observed share</th><th>Adjusted count (95% range)</th><th>Adjusted share (95% range)</th></tr></thead><tbody>' +
      years.map(row => '<tr><th scope="row">'+row.year+'</th><td>'+count(row.total)+'</td><td>'+count(row.observed)+'</td><td>'+percent(row.observed_share)+'</td><td>'+
        count(row.adjusted)+' ('+range(row.count_interval,count)+')</td><td>'+percent(row.adjusted_share)+' ('+range(row.share_interval,percent)+')</td></tr>').join('')+
      '</tbody></table>';
    get('architectureContent').hidden = false;
  }

  fetch('/architecture.json').then(response => {
    if (!response.ok) throw Error('Audit data unavailable');
    return response.json();
  }).then(render).catch(() => {
    get('architectureStatus').textContent = 'Could not load the architecture estimates. See the audit method and readings.';
  });
})();
