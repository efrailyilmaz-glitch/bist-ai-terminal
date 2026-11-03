"""V53 cross-sectional paper challenger portfolio constructor.
Converts ranked names into a constrained, diversified paper allocation.
No live order path. Weights are capped and can only be reduced by risk/liquidity constraints.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from .portfolio_analytics import _load
from .portfolio_guard import assess_frames
from .market_data import daily_frames

def _norm(w):
    a=np.maximum(np.asarray(w,float),0)
    s=float(a.sum())
    return a/s if s>0 else np.ones(len(a))/max(1,len(a))

def construct(ranked,portfolio_value=1_000_000,max_names=10,max_weight=.15,adv_limit_pct=1.0,method='score_inverse_vol'):
    rows=[x for x in (ranked or []) if x.get('ticker') and isinstance(x.get('score'),(int,float))]
    rows=sorted(rows,key=lambda x:float(x['score']),reverse=True)[:max(3,min(int(max_names),20))]
    if len(rows)<3:return {'status':'INSUFFICIENT_RANKED_NAMES'}
    codes=[x['ticker'].upper().replace('.IS','') for x in rows]
    rets,_=_load(codes)
    if rets is None or len(rets.columns)<3:return {'status':'NO_RISK_DATA'}
    valid=[c for c in codes if c in rets.columns]
    rows=[x for x in rows if x['ticker'].upper().replace('.IS','') in valid]
    scores=np.array([float(x['score']) for x in rows])
    scores=(scores-scores.min())+1e-6
    vol=rets[valid].std().values*np.sqrt(252)
    if method=='equal':raw=np.ones(len(valid))
    elif method=='inverse_vol':raw=1/np.maximum(vol,1e-8)
    else:raw=scores/np.maximum(vol,1e-8)
    w=_norm(raw)
    cap=max(1/len(valid),min(float(max_weight),.5))
    for _ in range(20):
        over=w>cap
        if not np.any(over):break
        excess=float((w[over]-cap).sum());w[over]=cap
        under=~over
        if np.any(under):w[under]+=_norm(w[under])*excess
        w=_norm(w)
    adv_lim=max(.1,min(float(adv_limit_pct),10))/100
    pv=max(1,float(portfolio_value));alloc=pv*w
    liquidity_flags=[];liq_mult=np.ones(len(valid))
    for i,x in enumerate(rows):
        adv=float(x.get('value_turnover') or 0)
        if adv<=0:
            liq_mult[i]=.5;liquidity_flags.append({'ticker':valid[i],'flag':'ADV_UNKNOWN'})
        elif alloc[i]>adv*adv_lim:
            liq_mult[i]=max(.2,min(1,(adv*adv_lim)/max(alloc[i],1)));liquidity_flags.append({'ticker':valid[i],'flag':'ADV_CAP','multiplier':round(float(liq_mult[i]),3)})
    w=_norm(w*liq_mult)
    cov=rets[valid].cov().values*252
    port_vol=math.sqrt(max(float(w@cov@w),0))
    corr=rets[valid].corr().fillna(0)
    avg_corr=float(np.mean([corr.iloc[i,j] for i in range(len(valid)) for j in range(i+1,len(valid))])) if len(valid)>1 else 0
    frames=daily_frames(valid+['XU100'])
    guard_rows=[]
    synthetic_positions={}
    for i,c in enumerate(valid):
        g=assess_frames(c,synthetic_positions,frames,'BUY')
        guard_rows.append({'ticker':c,'status':g.get('status'),'flags':g.get('flags'),'risk_multiplier':g.get('risk_multiplier')})
        if g.get('status')!='BLOCK':synthetic_positions[c]=max(1,int((pv*w[i])/max(float(rows[i].get('price') or 1),1)))
    return {'status':'OK','method':method,'portfolio_value':pv,'max_weight_pct':round(cap*100,1),
            'annual_volatility_pct':round(port_vol*100,2),'avg_correlation':round(avg_corr,3),
            'rows':[{'ticker':c,'weight_pct':round(float(w[i]*100),2),'allocation':round(float(pv*w[i]),2),
                     'score':round(float(rows[i]['score']),6),'volatility_pct':round(float(vol[i]*100),2)}
                    for i,c in enumerate(valid)],
            'liquidity_flags':liquidity_flags,'portfolio_guard':guard_rows,
            'policy':'Paper challenger allocation only. Liquidity/risk constraints can reduce exposure; never increase it above unconstrained baseline.'}
