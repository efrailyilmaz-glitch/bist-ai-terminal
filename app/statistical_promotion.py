"""V61 statistical confidence gate for XS promotion review.
Uses only prospective paper curve evidence. No historical backtest promotion.
"""
from __future__ import annotations
import math
import numpy as np

def _f(x,default=0.0):
    try:
        z=float(x)
        return z if math.isfinite(z) else default
    except Exception:return default

def _excess_increments(curve):
    rows=list(curve or [])
    if len(rows)<2:return []
    vals=[_f(x.get('excess_pct')) for x in rows]
    return [vals[i]-vals[i-1] for i in range(1,len(vals))]

def _regime_rows(curve):
    rows=list(curve or [])
    out={'UP':[],'DOWN':[],'FLAT':[]}
    for i in range(1,len(rows)):
        b0=_f(rows[i-1].get('benchmark_equity'));b1=_f(rows[i].get('benchmark_equity'))
        if b0<=0:continue
        br=b1/b0-1
        ex=_f(rows[i].get('excess_pct'))-_f(rows[i-1].get('excess_pct'))
        reg='UP' if br>.003 else 'DOWN' if br<-.003 else 'FLAT'
        out[reg].append(ex)
    return out

def bootstrap_confidence(curve,simulations=5000,seed=61,alpha=.05,test_count=3):
    inc=np.asarray(_excess_increments(curve),float)
    if len(inc)<20:
        return {'status':'INSUFFICIENT_STATISTICAL_SAMPLE','observations':int(len(inc))}
    sims=max(1000,min(int(simulations),20000));rng=np.random.default_rng(int(seed))
    means=np.empty(sims,float)
    n=len(inc)
    for i in range(sims):
        means[i]=rng.choice(inc,size=n,replace=True).mean()
    corrected_alpha=max(.001,min(.20,float(alpha)/max(1,int(test_count))))
    lo=float(np.quantile(means,corrected_alpha/2));hi=float(np.quantile(means,1-corrected_alpha/2))
    p_pos=float(np.mean(means>0))
    regs=_regime_rows(curve)
    regime={}
    negative_regimes=0
    for k,v in regs.items():
        arr=np.asarray(v,float)
        m=float(arr.mean()) if len(arr) else None
        if m is not None and m<0:negative_regimes+=1
        regime[k]={'n':int(len(arr)),'mean_excess_step':None if m is None else round(m,6),
                   'positive_step_pct':None if not len(arr) else round(float(np.mean(arr>0))*100,1)}
    reasons=[]
    if lo<=0:reasons.append('BOOTSTRAP_LOWER_BOUND_NOT_POSITIVE')
    if p_pos<.975:reasons.append('BOOTSTRAP_CONFIDENCE_BELOW_97_5')
    populated=sum(1 for x in regime.values() if x['n']>=5)
    if populated<2:reasons.append('REGIME_COVERAGE_INSUFFICIENT')
    if negative_regimes>=2:reasons.append('MULTI_REGIME_WEAKNESS')
    status='PASS' if not reasons else 'OBSERVE'
    return {'status':status,'reasons':reasons,'observations':int(n),'simulations':sims,'seed':int(seed),
            'multiple_testing':{'method':'BONFERRONI','test_count':int(test_count),'family_alpha':float(alpha),
                                'corrected_alpha':round(corrected_alpha,6)},
            'bootstrap':{'mean_excess_step':round(float(inc.mean()),6),'ci_low':round(lo,6),'ci_high':round(hi,6),
                         'prob_mean_positive_pct':round(p_pos*100,2)},
            'regimes':regime,
            'policy':'Prospective paper evidence only. Statistical confidence can veto promotion review but never enable live execution.'}

def evaluate(history,test_count=3):
    curve=list(reversed((history or {}).get('curve') or []))
    return bootstrap_confidence(curve,test_count=test_count)
