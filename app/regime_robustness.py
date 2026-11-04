"""V62 regime robustness gate for prospective XS promotion.
Evaluates forward paper excess separately across directional and high-volatility regimes.
"""
from __future__ import annotations
import math
import numpy as np

def _f(x,default=0.0):
    try:
        z=float(x)
        return z if math.isfinite(z) else default
    except Exception:return default

def classify(curve,vol_window=10,high_vol_quantile=.75):
    rows=list(curve or [])
    if len(rows)<2:return []
    bench=[]
    for i in range(1,len(rows)):
        b0=_f(rows[i-1].get('benchmark_equity'));b1=_f(rows[i].get('benchmark_equity'))
        bench.append((b1/b0-1) if b0>0 else 0.0)
    vols=[]
    for i in range(len(bench)):
        start=max(0,i-vol_window+1)
        arr=np.asarray(bench[start:i+1],float)
        vols.append(float(arr.std()) if len(arr)>=3 else 0.0)
    cutoff=float(np.quantile(np.asarray(vols,float),high_vol_quantile)) if vols else 0.0
    out=[]
    for i,br in enumerate(bench):
        ex=_f(rows[i+1].get('excess_pct'))-_f(rows[i].get('excess_pct'))
        if vols[i]>0 and vols[i]>=cutoff and cutoff>0:
            reg='HIGH_VOL'
        elif br>.003:
            reg='BULL'
        elif br<-.003:
            reg='BEAR'
        else:
            reg='RANGE'
        out.append({'regime':reg,'benchmark_return':br,'excess_step':ex,'volatility':vols[i]})
    return out

def evaluate(history,min_obs_per_regime=5,min_populated_regimes=3,max_negative_regimes=1):
    curve=list(reversed((history or {}).get('curve') or []))
    obs=classify(curve)
    if len(obs)<20:
        return {'status':'INSUFFICIENT_REGIME_SAMPLE','observations':len(obs)}
    result={}
    negative=0;populated=0
    for reg in ['BULL','BEAR','RANGE','HIGH_VOL']:
        vals=np.asarray([x['excess_step'] for x in obs if x['regime']==reg],float)
        if len(vals)>=min_obs_per_regime:populated+=1
        mean=float(vals.mean()) if len(vals) else None
        if len(vals)>=min_obs_per_regime and mean is not None and mean<0:negative+=1
        result[reg]={'n':int(len(vals)),
                     'mean_excess_step':None if mean is None else round(mean,6),
                     'median_excess_step':None if not len(vals) else round(float(np.median(vals)),6),
                     'positive_step_pct':None if not len(vals) else round(float(np.mean(vals>0))*100,1)}
    reasons=[]
    if populated<min_populated_regimes:reasons.append('REGIME_DIVERSITY_INSUFFICIENT')
    if negative>max_negative_regimes:reasons.append('TOO_MANY_NEGATIVE_REGIMES')
    hv=result['HIGH_VOL']
    if hv['n']>=min_obs_per_regime and hv['mean_excess_step'] is not None and hv['mean_excess_step']<0:
        reasons.append('HIGH_VOL_EDGE_NEGATIVE')
    bear=result['BEAR']
    if bear['n']>=min_obs_per_regime and bear['mean_excess_step'] is not None and bear['mean_excess_step']<0:
        reasons.append('BEAR_REGIME_EDGE_NEGATIVE')
    status='PASS' if not reasons else 'OBSERVE'
    return {'status':status,'reasons':list(dict.fromkeys(reasons)),'observations':len(obs),
            'populated_regimes':populated,'negative_regimes':negative,'regimes':result,
            'policy':'Prospective paper regime robustness can veto promotion review; it never increases risk or enables live execution.'}
