"""Estimate architecture prevalence from a stratified finite-population audit."""
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
DRAWS=60000

def read(name):
    return json.loads((HERE/name).read_text())

def limits(values):
    ordered=sorted(values)
    return [ordered[round(p*(len(ordered)-1))] for p in (.025,.975)]

def prediction(N,n,k,rng):
    # Jeffreys beta-binomial predictive distribution for the N-n unexamined outcomes.
    # Compute the discrete predictive mass by recurrence from j=0, in log space.
    m=N-n
    if m==0:return [k]*DRAWS
    a,b=k+.5,n-k+.5
    logs=[0.]
    for j in range(m):
        logs.append(logs[-1]+math.log((m-j)/(j+1))+math.log((a+j)/(b+m-j-1)))
    maximum=max(logs)
    return rng.choices(range(k,k+m+1),weights=[math.exp(x-maximum) for x in logs],k=DRAWS)

def exact_bounds(N,n,k,strata):
    # Invert inclusive hypergeometric tails with a Bonferroni familywise error bound.
    if N==n:return k,k
    threshold=math.comb(N,n)*.05/(2*strata)
    accepted=[]
    for total in range(k,N-n+k+1):
        lo=max(0,n-(N-total));hi=min(n,total)
        left=sum(math.comb(total,i)*math.comb(N-total,n-i) for i in range(lo,k+1))
        right=sum(math.comb(total,i)*math.comb(N-total,n-i) for i in range(k,hi+1))
        if left>=threshold and right>=threshold:accepted.append(total)
    return min(accepted),max(accepted)

def analyze():
    with (HERE/'frame.csv').open() as f:frame=list(csv.DictReader(f))
    blind={r['id']:r for r in read('blind.json')}
    a,b=read('reader_a.json'),read('reader_b.json')
    assert set(a)==set(b)==set(blind)=={r['id'] for r in frame if r['selected']=='1'}
    assert all(type(x['arch']) is bool and x['reason'].strip() for rr in (a,b) for x in rr.values())
    disputed={i for i in a if a[i]['arch']!=b[i]['arch']}
    resolution=read('reconciled.json')
    assert disputed==set(resolution) and all(type(x['arch']) is bool and x['reason'].strip() for x in resolution.values())
    details=[]
    groups=defaultdict(list)
    for row in frame:
        groups[int(row['year']),row['rating']].append(row)
        i=row['id']
        if i in blind:
            ref=resolution.get(i,a[i])
            details.append(dict(**row,title=blind[i]['title'],reader_a=a[i]['arch'],reader_a_reason=a[i]['reason'],reader_b=b[i]['arch'],
                                reader_b_reason=b[i]['reason'],architecture=ref['arch'],reason=ref['reason']))
    def write_csv(name,rows):
        with (HERE/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    write_csv('audit_rows.csv',details)
    final={r['id']:r['architecture'] for r in details}
    rng=random.Random(20261117)
    strata=[]
    years=[]
    draws={}
    for year in (2025,2026):
        total=observed=fixed=0
        estimate=0.
        simulations=[0]*DRAWS
        exact=[0,0]
        for rating in ('1','2','3','U'):
            group=groups[year,rating]
            eligible=[r for r in group if r['previous_review']=='Batch reading']
            carried=len(group)-len(eligible)
            assigned=carried if rating=='3' else 0
            sample=[r['id'] for r in eligible if r['id'] in final]
            N,n,k=len(eligible),len(sample),sum(final[i] for i in sample)
            assert n==min(40,N) and n>0
            total+=len(group); observed+=len(group) if rating=='3' else 0
            fixed+=carried; estimate+=assigned+N*k/n
            sampled=prediction(N,n,k,rng)
            simulations=[x+y+assigned for x,y in zip(simulations,sampled)]
            endpoints=exact_bounds(N,n,k,6)
            exact=[v+t+assigned for v,t in zip(exact,endpoints)]
            strata.append(dict(year=year,rating=rating,total=len(group),carried=carried,carried_arch=assigned,eligible=N,
                               sample=n,architecture=k,expansion_weight=N/n,adjusted_count=assigned+N*k/n))
        draws[year]=simulations
        year_stats=dict(year=year,total=total,observed=observed,observed_share=100*observed/total,adjusted=estimate,
                        adjusted_share=100*estimate/total,count_interval=limits(simulations),carried=fixed,exact_count_interval=exact)
        year_stats['share_interval']=[100*v/total for v in year_stats['count_interval']]
        years.append(year_stats)
    write_csv('strata.csv',strata)
    old,new=years
    delta=new['adjusted']-old['adjusted']
    pp=new['adjusted_share']-old['adjusted_share']
    differences=[b-a for a,b in zip(draws[2025],draws[2026])]
    shares=[100*(b/new['total']-a/old['total']) for a,b in zip(draws[2025],draws[2026])]
    exact_pp=[100*(new['exact_count_interval'][j]/new['total']-old['exact_count_interval'][1-j]/old['total']) for j in [0,1]]
    result=dict(years=years,difference=dict(count=delta,share_pp=pp,count_interval=limits(differences),share_interval=limits(shares),
        exact_share_interval=exact_pp),sample=len(a),agreement=len(a)-len(disputed),reader_confusion={
        f'{left}/{right}':sum((a[i]['arch'],b[i]['arch'])==(left,right) for i in a) for left in [True,False] for right in [True,False]})
    (HERE/'architecture.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
if __name__=='__main__':analyze()
