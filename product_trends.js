const productLevels = ['1','2','3','4','5','U','NA'];
const productNames = {...magnitudeNames, NA:'Outside scale'};
const productColors = {'1':'#b6cfcd','2':'#619d98','3':'#116d68','4':'#d99136','5':'#963e28',U:'#9b81a6',NA:'#d9dddf'};

function drawProductTrends() {
  if (!data) return;
  const share = el('productUnit').value === 'share';
  const monthly = data.product_monthly || [];
  const annualRows = data.product_annual || [];
  el('productCoverage').textContent = fmt(monthly.reduce((sum,r)=>sum+r.n,0))+' of '+fmt(data.total)+' filtered announcements have magnitude decisions.';
  const months = [];
  for (let year=2021; year<=2026; year++) for(let month=1;month<=(year===2026?10:12);month++) months.push(`${year}-${String(month).padStart(2,'0')}`);
  const lookup = new Map(monthly.map(r=>[r.month+'|'+r.level,r.n]));
  const totals = months.map(m=>productLevels.reduce((sum,k)=>sum+(lookup.get(m+'|'+k)||0),0));
  const max = share ? 100 : Math.max(1,...totals);
  const width=1120, left=48, top=16, height=235, step=(width-left-16)/months.length;
  let svg=`<svg class="chart" viewBox="0 0 ${width} 300" role="group" aria-label="Monthly announcement counts by product-change magnitude, January 2021 through October 28, 2026">`;
  for(let tick=0;tick<=4;tick++) {
    const value=max*tick/4, y=top+height-height*tick/4;
    svg+=`<line x1="${left}" y1="${y}" x2="${width-16}" y2="${y}" stroke="#e1e7e3"/><text x="${left-6}" y="${y+4}" text-anchor="end" class="axis">${Math.round(value)}${share?'%':''}</text>`;
  }
  months.forEach((month,index)=>{
    let bottom=top+height;
    productLevels.forEach(level=>{
      const n=lookup.get(month+'|'+level)||0;
      if(!n)return;
      const value=share?100*n/totals[index]:n, h=height*value/max;
      bottom-=h;
      svg+=`<rect class="point" tabindex="0" role="button" data-month="${month}" data-level="${level}" x="${left+step*index}" y="${bottom}" width="${Math.max(1,step-2)}" height="${h}" fill="${productColors[level]}" aria-label="${month}: ${productNames[level]}, ${n} announcements"><title>${month}: ${productNames[level]} — ${fmt(n)}${share?' ('+value.toFixed(1)+'%)':''}</title></rect>`;
    });
    if(month.endsWith('-01')) svg+=`<text x="${left+step*index}" y="${top+height+22}" class="axis">${month.slice(0,4)}</text>`;
  });
  svg+='<text x="1104" y="291" text-anchor="end" class="axis">October 2026 ends on the 28th</text></svg>';
  el('productMonthly').innerHTML=svg;
  el('productLegend').innerHTML=productLevels.map(k=>`<span style="white-space:nowrap"><i class="legend" style="background:${productColors[k]}"></i>${esc(productNames[k])}</span>`).join(' ');
  const yearly = new Map(annualRows.map(r=>[r.year+'|'+r.level,r.n]));
  let table='<table class="bars"><thead><tr><th>Magnitude</th>'+[2021,2022,2023,2024,2025,2026].map(y=>`<th>${y}</th>`).join('')+'</tr></thead><tbody>';
  productLevels.forEach(level=>{
    table+=`<tr><th>${esc(productNames[level])}</th>`;
    for(let year=2021;year<=2026;year++) {
      const n=yearly.get(year+'|'+level)||0;
      table+=`<td><button data-year="${year}" data-level="${level}" aria-label="${year}: ${productNames[level]}, ${n} announcements">${fmt(n)}</button></td>`;
    }
    table+='</tr>';
  });
  const inScope = year=>productLevels.filter(k=>k!=='NA').reduce((sum,k)=>sum+(yearly.get(year+'|'+k)||0),0);
  table+='<tr><th>In-scale total (including U)</th>'+[2021,2022,2023,2024,2025,2026].map(y=>`<td>${fmt(inScope(y))}</td>`).join('')+'</tr>';
  table+='<tr><th>In-scale year-over-year change</th>'+[2021,2022,2023,2024,2025,2026].map(y=>`<td>${y===2021||!inScope(y-1)?'—':((inScope(y)/inScope(y-1)-1)*100).toFixed(1)+'%'}</td>`).join('')+'</tr></tbody></table>';
  el('productAnnual').innerHTML=table;
  const drill=e=>{
    const target=e.target.closest('[data-level]');
    if(!target)return;
    const month=target.dataset.month, year=target.dataset.year;
    if(month){const [y,m]=month.split('-').map(Number);const last=month==='2026-10'?28:new Date(Date.UTC(y,m,0)).getUTCDate();selectPeriod(month+'-01',month+'-'+last,'',target.dataset.level,false);}
    else selectPeriod(year+'-01-01',year+'-10-28','',target.dataset.level,false);
  };
  el('productMonthly').onclick=drill;
  el('productMonthly').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();drill(e);}};
  el('productAnnual').onclick=drill;
  el('productValues').innerHTML='<table class="bars"><thead><tr><th>Month</th>'+productLevels.map(k=>`<th>${esc(productNames[k])}</th>`).join('')+'</tr></thead><tbody>'+months.map(m=>'<tr><th>'+m+'</th>'+productLevels.map(k=>'<td>'+fmt(lookup.get(m+'|'+k)||0)+'</td>').join('')+'</tr>').join('')+'</tbody></table>';
}
