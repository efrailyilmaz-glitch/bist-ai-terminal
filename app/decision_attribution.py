"""V72 forward-only decision attribution 2.0.
Adds bootstrap confidence intervals, Benjamini-Hochberg FDR control and regime-aware
association diagnostics. Uses only settled prospective evidence; association is not causality.
"""
from __future__ import annotations
import hashlib,json,math,statistics
import numpy as np
from . import experience_engine as ex

def _feature_map(setup):
    out={}
    for x in (setup.get('confirmations') or []):out['confirm:'+str(x)]=1
    for x in (setup.get('warnings') or []):out['warning:'+str(x)]=1
    comps=setup.get('components') or {}
    for k,v in comps.items():
        if isinstance(v,(int,float)) and math.isfinite(float(v)):
            z=float(v);out['component:'+str(k)+':high']=1 if z>=70 else 0
            out['component:'+str(k)+':low']=1 if z<=30 else 0
    guard=(setup.get('signal_guard') or {}).get('status')
    trap=(setup.get('trap_defense') or {}).get('status')
    if guard:out['signal_guard:'+str(guard)]=1
    if trap:out['trap_defense:'+str(trap)]=1
    return {k:v for k,v in out.items() if v}

def _mean(xs):return sum(xs)/len(xs) if xs else None
def _median(xs):return statistics.median(xs) if xs else None

def _seed(feature,horizon):
    return int(hashlib.sha256((str(feature)+'|'+str(horizon)).encode()).hexdigest()[:8],16)

def _bootstrap_delta(yes,no,simulations=3000,seed=72):
    a=np.asarray(yes,float);b=np.asarray(no,float)
    if len(a)<2 or len(b)<2:return None
    rng=np.random.default_rng(int(seed));sims=max(1000,min(int(simulations),10000))
    d=np.empty(sims,float)
    for i in range(sims):
        d[i]=rng.choice(a,size=len(a),replace=True).mean()-rng.choice(b,size=len(b),replace=True).mean()
    pneg=float(np.mean(d<=0));ppos=float(np.mean(d>=0))
    p=min(1.0,max(1/sims,2*min(pneg,ppos)))
    return {'ci_low':float(np.quantile(d,.025)),'ci_high':float(np.quantile(d,.975)),
            'p_value':p,'prob_positive':float(np.mean(d>0)),'simulations':sims}

def _bh_qvalues(rows):
    vals=[(i,float(r['p_value'])) for i,r in enumerate(rows) if isinstance(r.get('p_value'),(int,float))]
    if not vals:return
    vals.sort(key=lambda x:x[1]);m=len(vals);qs=[None]*m;running=1.0
    for rank in range(m,0,-1):
        idx,p=vals[rank-1]
        q=min(running,p*m/rank);running=q;qs[rank-1]=(idx,min(1.0,q))
    for item in qs:
        if item is not None:rows[item[0]]['fdr_q_value']=item[1]

def _regime_diag(parsed,feature,min_regime_samples=5):
    regs={}
    for r,m in parsed:
        reg=str(r.get('regime') or 'UNKNOWN').upper()
        bucket=regs.setdefault(reg,{'yes':[],'no':[]})
        bucket['yes' if m.get(feature) else 'no'].append(float(r['excess']))
    out={};signs=[]
    for reg,b in regs.items():
        yes,no=b['yes'],b['no'];delta=None
        if len(yes)>=min_regime_samples and len(no)>=min_regime_samples:
            delta=(_mean(yes) or 0)-(_mean(no) or 0)
            if abs(delta)>=.4:signs.append(1 if delta>0 else -1)
        out[reg]={'with_n':len(yes),'without_n':len(no),
                  'delta_mean_excess_pct':None if delta is None else round(delta,3)}
    conflict=(1 in signs and -1 in signs)
    return out,conflict

def attribution(horizon=20,min_samples=12,simulations=3000,fdr_alpha=.10):
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    with ex._LOCK:
        c=ex._conn();c.row_factory=__import__('sqlite3').Row
        rows=[dict(x) for x in c.execute(f'''SELECT id,ticker,regime,setup_json,settled_{horizon} AS settled,excess_{horizon} AS excess
                                             FROM signals WHERE settled_{horizon}=1 AND excess_{horizon} IS NOT NULL
                                             ORDER BY id''').fetchall()];c.close()
    parsed=[]
    for r in rows:
        try:setup=json.loads(r.get('setup_json') or '{}')
        except Exception:setup={}
        parsed.append((r,_feature_map(setup)))
    universe=sorted({k for _,m in parsed for k in m})
    result=[];base=_mean([float(r['excess']) for r,_ in parsed]) or 0.0
    for f in universe:
        yes=[float(r['excess']) for r,m in parsed if m.get(f)]
        no=[float(r['excess']) for r,m in parsed if not m.get(f)]
        delta=None;boot=None
        if len(yes)>=min_samples and len(no)>=min_samples:
            delta=(_mean(yes) or 0)-(_mean(no) or 0)
            boot=_bootstrap_delta(yes,no,simulations,_seed(f,horizon))
        regimes,regime_conflict=_regime_diag(parsed,f)
        result.append({'feature':f,'with_n':len(yes),'without_n':len(no),
                       'with_mean_excess_pct':None if not yes else round(_mean(yes),3),
                       'without_mean_excess_pct':None if not no else round(_mean(no),3),
                       'with_median_excess_pct':None if not yes else round(_median(yes),3),
                       'delta_mean_excess_pct':None if delta is None else round(delta,3),
                       'delta_ci_low':None if not boot else round(boot['ci_low'],3),
                       'delta_ci_high':None if not boot else round(boot['ci_high'],3),
                       'p_value':None if not boot else round(boot['p_value'],6),
                       'fdr_q_value':None,'prob_delta_positive_pct':None if not boot else round(boot['prob_positive']*100,2),
                       'regimes':regimes,'regime_conflict':regime_conflict,'label':'UNKNOWN'})
    _bh_qvalues(result)
    for r in result:
        d=r.get('delta_mean_excess_pct');lo=r.get('delta_ci_low');hi=r.get('delta_ci_high');q=r.get('fdr_q_value')
        if d is None or q is None:
            lab='UNKNOWN'
        elif r.get('regime_conflict'):
            lab='CONFLICTED'
        elif q<=fdr_alpha and hi is not None and hi<0 and d<=-.4 and (r.get('with_mean_excess_pct') or 0)<0:
            lab='NEGATIVE'
        elif q<=fdr_alpha and lo is not None and lo>0 and d>=.4 and (r.get('with_mean_excess_pct') or 0)>0:
            lab='CONSISTENT'
        elif abs(d)>=.4:
            lab='POSSIBLE'
        else:lab='UNKNOWN'
        r['label']=lab
        if isinstance(r.get('fdr_q_value'),float):r['fdr_q_value']=round(r['fdr_q_value'],6)
    order={'NEGATIVE':0,'CONSISTENT':1,'CONFLICTED':2,'POSSIBLE':3,'UNKNOWN':4}
    result.sort(key=lambda x:(order.get(x['label'],9),-(abs(x['delta_mean_excess_pct']) if x['delta_mean_excess_pct'] is not None else -1),x['feature']))
    prune=[x for x in result if x['label']=='NEGATIVE']
    return {'status':'OK','version':'72.0','horizon':horizon,'settled_signals':len(rows),
            'baseline_mean_excess_pct':round(base,3),'fdr_method':'BENJAMINI_HOCHBERG','fdr_alpha':float(fdr_alpha),
            'bootstrap_simulations':max(1000,min(int(simulations),10000)),
            'rows':result,'prune_candidates':prune,
            'note':'Forward-only prospective association with bootstrap CI, FDR control and regime diagnostics. Labels are not causal claims and never directly mutate champion logic.'}

def feature_report():
    return {'5d':attribution(5),'20d':attribution(20),'60d':attribution(60)}
