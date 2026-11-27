"""Recalculate descriptive trends from reviewed row-level decisions; no relabelling."""
import calendar
import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GROUPS = {'all': {'1','2','3','4','5','NA','U'}, 'parameter': {'1'},
          'refinement': {'2'}, 'broad': {'2','3','4','5'},
          'strict': {'3','4','5'}, 'outside': {'NA'}, 'unresolved': {'U'}}

def write_csv(name, rows):
    with (HERE/name).open('w', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def growth(current, previous):
    return 100*(current/previous-1) if previous else None

def measure(rows, start, end):
    selected=[r for r in rows if start <= r['_date'] <= end]
    counts=Counter(r['product_change_level'] for r in selected)
    result={'start':str(start),'end':str(end),'days':(end-start).days+1}
    for name,levels in GROUPS.items():
        result[name]=sum(counts[level] for level in levels)
        result[name+'_per_30_days']=result[name]*30/result['days']
    assert result['all']==result['parameter']+result['broad']+result['outside']+result['unresolved']
    assert result['broad']==result['refinement']+result['strict']
    return result

def main():
    source=ROOT/'product_change/announcements.csv'
    rows=list(csv.DictReader(source.open(newline='')))
    assert len(rows)==22588 and len({r['source_url'] for r in rows})==22588
    for r in rows:
        r['_date']=date.fromisoformat(r['announcement_date'])
        assert r['product_change_level'] in GROUPS['all']
    years=[]
    for year in range(2021,2027):
        m={'year':year,**measure(rows,date(year,1,1),date(year,10,28))}
        for group in ('all','parameter','broad','strict'):
            m[group+'_share_pct']=100*m[group]/m['all']
            m[group+'_yoy_pct']=growth(m[group],years[-1][group]) if years else None
            m[group+'_rate_yoy_pct']=growth(m[group+'_per_30_days'],years[-1][group+'_per_30_days']) if years else None
        for group in ('broad','strict'):
            m[group+'_u_only_yoy_low_pct']=growth(m[group],years[-1][group]+years[-1]['unresolved']) if years else None
            m[group+'_u_only_yoy_high_pct']=growth(m[group]+m['unresolved'],years[-1][group]) if years else None
        years.append(m)
    # Reconcile independent row aggregation to published matched aggregates.
    published=list(csv.DictReader((ROOT/'product_change/matched.csv').open()))
    for m in years:
        for group,levels in GROUPS.items():
            assert m[group]==sum(int(r['announcements']) for r in published if int(r['year'])==m['year'] and r['level'] in levels)
    months=[]
    for year in range(2021,2027):
        for month in range(1,13 if year<2026 else 11):
            end=date(year,month,28 if (year,month)==(2026,10) else calendar.monthrange(year,month)[1])
            months.append({'month':f'{year}-{month:02}',**measure(rows,date(year,month,1),end)})
    recent=[]
    for year in (2025,2026):
        end=date(year,10,28)
        for label,offset in [('latest_90_days',0),('preceding_90_days',90)]:
            finish=end-timedelta(days=offset)
            recent.append({'year':year,'period':label,**measure(rows,finish-timedelta(days=89),finish)})
    services=[]
    tags=sorted({s for r in rows for s in r['service'].split('; ')})
    for tag in tags:
        srows=[r for r in rows if tag in r['service'].split('; ')]
        a=measure(srows,date(2025,1,1),date(2025,10,28));b=measure(srows,date(2026,1,1),date(2026,10,28))
        services.append({'service':tag,'broad_2025':a['broad'],'broad_2026':b['broad'],'broad_delta':b['broad']-a['broad'],
                         'strict_2025':a['strict'],'strict_2026':b['strict'],'strict_delta':b['strict']-a['strict']})
    services.sort(key=lambda r:(-r['strict_delta'],r['service']))
    for name,data in [('annual_matched.csv',years),('monthly.csv',months),('velocity_90_days.csv',recent),('service_changes.csv',services)]:write_csv(name,data)
    result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'definitions':{k:sorted(v) for k,v in GROUPS.items()},'annual':years,'velocity':recent,
            'limits':['Descriptive corpus trends, not exhaustive AWS output.','AI-reviewed labels, not human ground truth.','U-only sensitivity excludes errors among assigned labels.','Broad and strict thresholds are analysis choices, not new taxonomy labels.']}
    (HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    os.environ.setdefault('MPLCONFIGDIR',tempfile.gettempdir()+'/aws-trend-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'svg.hashsalt':'aws-substantive-2026-11-25','font.size':10})
    fig,axes=plt.subplots(2,1,figsize=(11,8),layout='constrained')
    for group,label,color in [('all','All announcements','#a3a9ad'),('broad','Refinements and additions (2–5)','#528f89'),('strict','New capabilities and larger additions (3–5)','#173d57')]:
        axes[0].plot([m['year'] for m in years],[m[group] for m in years],marker='o',label=label,color=color)
    axes[0].set(title='Matched annual periods: 1 January–28 October',ylabel='Announcements',ylim=(0,None));axes[0].legend(loc='upper left',fontsize=9)
    for group,label,color in [('broad','Levels 2–5','#528f89'),('strict','Levels 3–5','#173d57')]:
        axes[1].plot([date.fromisoformat(m['start']) for m in months],[m[group+'_per_30_days'] for m in months],label=label,color=color)
    axes[1].set(title='Monthly publication rate, normalised to 30 calendar days',ylabel='Announcements per 30 days',ylim=(0,None));axes[1].legend()
    for ax in axes:ax.grid(axis='y',alpha=.2)
    fig.suptitle('Reviewed AWS announcements: substantive trend comparisons',fontsize=15)
    fig.supxlabel('Collected corpus only · AI labels · Rare-category trends provisional · October 2026 ends on day 28',fontsize=9)
    fig.savefig(HERE/'trends.svg',metadata={'Date':None});fig.savefig(HERE/'trends.png',dpi=150);plt.close(fig)
    print(json.dumps({'latest_annual':years[-1],'velocity':recent,'top_service_increases':services[:8]},indent=2))

if __name__=='__main__':main()
