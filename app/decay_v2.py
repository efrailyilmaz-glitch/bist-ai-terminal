"""V69 forward-only strategy/model decay 2.0.
Adds confidence-aware degradation for paper trade strategies and regime-aware decay for XS portfolios.
Decay can veto promotion/allocation confidence; it never auto-liquidates positions.
"""
from __future__ import annotations
import math
import numpy as np
from .strategy_decay import detect_decay as legacy_decay

def _finite(x):
    try:
        z=float(x);return z if math.isfinite(z) else None
    except Exception:return None

def _bootstrap_mean(values,simulations=3000,seed=69):
    x=np.asarray([float(v) for v in values if _finite(v) is not None],float)
    if len(x)<8:return {'status':'INSUFFICIENT','n':len(x)}
    rng=np.random.default_rng(seed);means=np.empty(simulations,float)
    for i in range(simulations):means[i]=rng.choice(x,size=len(x),replace=True).mean()
    return {'status':'OK','n':len(x),'mean':float(x.mean()),'ci_low':float(np.quantile(means,.025)),
            'ci_high':float(np.quantile(means,.975)),'prob_positive':float(np.mean(means>0))}

def detect_trade_decay(bot,min_trades=24,window=12):
    base=legacy_decay(bot,min_trades,window)
    exits=[o for o in reversed((bot or {}).get('orders') or []) if isinstance(o.get('pnl'),(int,float))]
    pnls=[float(o['pnl']) for o in exits]
    if len(pnls)<min_trades:return {**base,'v2_status':'INSUFFICIENT','confidence':{'status':'INSUFFICIENT','n':len(pnls)}}
    w=max(8,min(int(window),len(pnls)//2))
    prior=pnls[-2*w:-w];recent=pnls[-w:]
    pc=_bootstrap_mean(prior,seed=68);rc=_bootstrap_mean(recent,seed=69)
    flags=list(base.get('flags') or []);score=int(base.get('score') or 0)
    if rc.get('status')=='OK':
        if rc['ci_high']<0:flags.append('RECENT_EXPECTANCY_CONFIDENTLY_NEGATIVE');score+=30
        elif rc['prob_positive']<.25:flags.append('RECENT_EXPECTANCY_LOW_CONFIDENCE');score+=15
    if pc.get('status')=='OK' and rc.get('status')=='OK':
        scale=max(abs(pc['mean']),1e-9)
        if pc['mean']>0 and rc['mean']<pc['mean']*.25:
            flags.append('CONFIDENCE_AWARE_EDGE_COLLAPSE');score+=15
    status='DECAY' if score>=55 else 'WATCH' if score>=30 else 'STABLE'
    return {**base,'v2_status':status,'status':status,'score':min(100,score),'flags':list(dict.fromkeys(flags)),
            'confidence':{'prior':pc,'recent':rc},
            'note':'Forward paper decay 2.0. Confidence-aware degradation can veto promotion; it never auto-liquidates.'}

def _curve_steps(history):
    curve=list(reversed((history or {}).get('curve') or []))
    out=[]
    for i in range(1,len(curve)):
        ex0=_finite(curve[i-1].get('excess_pct'));ex1=_finite(curve[i].get('excess_pct'))
        b0=_finite(curve[i-1].get('benchmark_equity'));b1=_finite(curve[i].get('benchmark_equity'))
        if ex0 is None or ex1 is None:continue
        br=(b1/b0-1) if b0 and b1 else 0.0
        reg='BULL' if br>.003 else 'BEAR' if br<-.003 else 'RANGE'
        out.append({'excess':ex1-ex0,'regime':reg})
    return out

def detect_xs_decay(history,min_steps=30,window=15):
    steps=_curve_steps(history)
    rebs=list(reversed((history or {}).get('rebalances') or []))
    if len(steps)<min_steps:
        return {'status':'INSUFFICIENT','score':0,'flags':['MIN_FORWARD_CURVE_STEPS'],'steps':len(steps)}
    w=max(10,min(int(window),len(steps)//2))
    prior=[x['excess'] for x in steps[-2*w:-w]];recent=[x['excess'] for x in steps[-w:]]
    pc=_bootstrap_mean(prior,seed=68);rc=_bootstrap_mean(recent,seed=69)
    flags=[];score=0
    if rc.get('status')=='OK':
        if rc['ci_high']<0:flags.append('RECENT_EXCESS_CONFIDENTLY_NEGATIVE');score+=40
        elif rc['prob_positive']<.25:flags.append('RECENT_EXCESS_LOW_CONFIDENCE');score+=20
    if pc.get('status')=='OK' and rc.get('status')=='OK' and pc['mean']>0:
        if rc['mean']<0:flags.append('EXCESS_SIGN_FLIP');score+=30
        elif rc['mean']<pc['mean']*.25:flags.append('EXCESS_COLLAPSE');score+=20
    regime={}
    for reg in ['BULL','BEAR','RANGE']:
        p=[x['excess'] for x in steps[-2*w:-w] if x['regime']==reg]
        r=[x['excess'] for x in steps[-w:] if x['regime']==reg]
        pm=float(np.mean(p)) if p else None;rm=float(np.mean(r)) if r else None
        regime[reg]={'prior_n':len(p),'recent_n':len(r),'prior_mean':pm,'recent_mean':rm}
        if len(p)>=3 and len(r)>=3 and pm is not None and rm is not None and pm>0 and rm<0:
            flags.append(reg+'_REGIME_SIGN_FLIP');score+=10
    if len(rebs)>=6:
        n=max(3,min(6,len(rebs)//2))
        prior_reb=rebs[-2*n:-n];recent_reb=rebs[-n:]
        pt=np.mean([float(x.get('turnover_pct') or 0) for x in prior_reb]) if prior_reb else 0
        rt=np.mean([float(x.get('turnover_pct') or 0) for x in recent_reb]) if recent_reb else 0
        pcost=np.mean([float(x.get('cost') or 0) for x in prior_reb]) if prior_reb else 0
        rcost=np.mean([float(x.get('cost') or 0) for x in recent_reb]) if recent_reb else 0
        if pt>0 and rt>pt*1.75:flags.append('TURNOVER_DECAY');score+=10
        if pcost>0 and rcost>pcost*1.75:flags.append('COST_DECAY');score+=10
    status='DECAY' if score>=55 else 'WATCH' if score>=30 else 'STABLE'
    return {'status':status,'score':min(100,score),'flags':list(dict.fromkeys(flags)),'steps':len(steps),'window':w,
            'confidence':{'prior':pc,'recent':rc},'regimes':regime,
            'note':'Prospective XS decay 2.0. Uses only forward curve/rebalance evidence; no backtest evidence and no auto-liquidation.'}
