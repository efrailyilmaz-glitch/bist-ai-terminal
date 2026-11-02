"""V46 forward-only decision attribution and feature-pruning diagnostics.
Uses only settled prospective ledger rows. Association, not causality.
"""
from __future__ import annotations
import json, math, statistics
from . import experience_engine as ex

def _feature_map(setup):
    out={}
    for x in (setup.get('confirmations') or []): out['confirm:'+str(x)]=1
    for x in (setup.get('warnings') or []): out['warning:'+str(x)]=1
    comps=setup.get('components') or {}
    for k,v in comps.items():
        if isinstance(v,(int,float)) and math.isfinite(float(v)):
            z=float(v);out['component:'+str(k)+':high']=1 if z>=70 else 0
            out['component:'+str(k)+':low']=1 if z<=30 else 0
    guard=(setup.get('signal_guard') or {}).get('status')
    trap=(setup.get('trap_defense') or {}).get('status')
    if guard: out['signal_guard:'+str(guard)]=1
    if trap: out['trap_defense:'+str(trap)]=1
    return {k:v for k,v in out.items() if v}

def _mean(xs): return sum(xs)/len(xs) if xs else None
def _median(xs): return statistics.median(xs) if xs else None

def attribution(horizon=20,min_samples=12):
    if horizon not in (5,20,60): raise ValueError('horizon must be 5, 20 or 60')
    with ex._LOCK:
        c=ex._conn();c.row_factory=__import__('sqlite3').Row
        rows=[dict(x) for x in c.execute(f'''SELECT id,ticker,setup_json,settled_{horizon} AS settled,excess_{horizon} AS excess
                                             FROM signals WHERE settled_{horizon}=1 AND excess_{horizon} IS NOT NULL
                                             ORDER BY id''').fetchall()];c.close()
    parsed=[]
    for r in rows:
        try:setup=json.loads(r.get('setup_json') or '{}')
        except Exception:setup={}
        parsed.append((r,_feature_map(setup)))
    universe=sorted({k for _,m in parsed for k in m})
    result=[]
    all_ex=[float(r['excess']) for r,_ in parsed]
    base=_mean(all_ex) or 0.0
    for f in universe:
        yes=[float(r['excess']) for r,m in parsed if m.get(f)]
        no=[float(r['excess']) for r,m in parsed if not m.get(f)]
        if len(yes)<min_samples or len(no)<min_samples:
            label='UNKNOWN';delta=None
        else:
            delta=(_mean(yes) or 0)-(_mean(no) or 0)
            if delta<=-1.0 and (_mean(yes) or 0)<0:label='NEGATIVE'
            elif delta>=1.0 and (_mean(yes) or 0)>0:label='CONSISTENT'
            elif abs(delta)>=.4:label='POSSIBLE'
            else:label='UNKNOWN'
        result.append({'feature':f,'with_n':len(yes),'without_n':len(no),
                       'with_mean_excess_pct':None if not yes else round(_mean(yes),3),
                       'without_mean_excess_pct':None if not no else round(_mean(no),3),
                       'with_median_excess_pct':None if not yes else round(_median(yes),3),
                       'delta_mean_excess_pct':None if delta is None else round(delta,3),
                       'label':label})
    order={'NEGATIVE':0,'CONSISTENT':1,'POSSIBLE':2,'UNKNOWN':3}
    result.sort(key=lambda x:(order[x['label']], -(abs(x['delta_mean_excess_pct']) if x['delta_mean_excess_pct'] is not None else -1), x['feature']))
    prune=[x for x in result if x['label']=='NEGATIVE']
    return {'status':'OK','horizon':horizon,'settled_signals':len(rows),'baseline_mean_excess_pct':round(base,3),
            'rows':result,'prune_candidates':prune,
            'note':'Forward-only association report. Labels are not causal claims and do not automatically mutate strategy logic.'}

def feature_report():
    return {'5d':attribution(5),'20d':attribution(20),'60d':attribution(60)}
