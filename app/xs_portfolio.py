"""V66 constrained XS paper portfolio constructor.
Risk/liquidity/capacity constraints can only reduce target exposure; removed exposure stays cash.
No live order path.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from .portfolio_analytics import _load
from .portfolio_guard import assess_frames
from .market_data import daily_frames
from .xs_capacity import assess as capacity_assess, portfolio_summary as capacity_summary

def _norm(w):
    a=np.maximum(np.asarray(w,float),0)
    s=float(a.sum())
    return a/s if s>0 else np.zeros(len(a))

def _median_value_turnover(df):
    if df is None or df.empty or 'Close' not in df or 'Volume' not in df:return None
    c=pd.to_numeric(df['Close'],errors='coerce')
    v=pd.to_numeric(df['Volume'],errors='coerce')
    x=(c*v).replace([np.inf,-np.inf],np.nan).dropna().tail(20)
    return None if x.empty else float(x.median())

def _last_bar(df):
    if df is None or df.empty:return {}
    r=df.iloc[-1]
    def g(k):
        try:
            z=float(r.get(k))
            return z if math.isfinite(z) else None
        except Exception:return None
    return {'price':g('Close'),'high':g('High'),'low':g('Low')}

def construct(ranked,portfolio_value=1_000_000,max_names=10,max_weight=.15,adv_limit_pct=1.0,
              method='score_inverse_vol',current_weights=None):
    rows=[x for x in (ranked or []) if x.get('ticker') and isinstance(x.get('score'),(int,float))]
    rows=sorted(rows,key=lambda x:float(x['score']),reverse=True)[:max(3,min(int(max_names),20))]
    if len(rows)<3:return {'status':'INSUFFICIENT_RANKED_NAMES'}
    codes=[x['ticker'].upper().replace('.IS','') for x in rows]
    rets,_=_load(codes)
    if rets is None or len(rets.columns)<3:return {'status':'NO_RISK_DATA'}
    valid=[c for c in codes if c in rets.columns]
    rows=[x for x in rows if x['ticker'].upper().replace('.IS','') in valid]
    if len(valid)<3:return {'status':'NO_RISK_DATA'}
    scores=np.array([float(x['score']) for x in rows])
    scores=(scores-scores.min())+1e-6
    vol=rets[valid].std().values*np.sqrt(252)
    if method=='equal':raw=np.ones(len(valid))
    elif method=='inverse_vol':raw=1/np.maximum(vol,1e-8)
    else:raw=scores/np.maximum(vol,1e-8)
    baseline=_norm(raw)
    cap=max(.01,min(float(max_weight),.50))
    # Absolute cap: clipped exposure is cash, never redistributed.
    w=np.minimum(baseline,cap)
    pv=max(1,float(portfolio_value))
    frames=daily_frames(valid+['XU100'])
    current={str(k).upper().replace('.IS',''):max(0,float(v)) for k,v in (current_weights or {}).items()}
    liquidity_flags=[];guard_rows=[];capacity_rows=[]
    synthetic_positions={}
    for i,code in enumerate(valid):
        before=float(w[i])
        adv=_median_value_turnover(frames.get(code))
        if not adv:
            try:adv=float(rows[i].get('value_turnover') or 0)
            except Exception:adv=0.0
        # Simple liquidity pre-guard. Never renormalize after reduction.
        if adv<=0:
            w[i]*=.5;liquidity_flags.append({'ticker':code,'flag':'ADV_UNKNOWN','multiplier':.5})
        else:
            cap_notional=adv*max(.001,min(float(adv_limit_pct)/100,.10))
            target=pv*w[i]
            if target>cap_notional:
                mult=max(0.0,min(1.0,cap_notional/max(target,1)))
                w[i]*=mult
                liquidity_flags.append({'ticker':code,'flag':'ADV_CAP','multiplier':round(mult,3)})
        g=assess_frames(code,synthetic_positions,frames,'BUY')
        rm=max(0.0,min(1.0,float(g.get('risk_multiplier',1.0) if g.get('risk_multiplier') is not None else .75)))
        if g.get('status')=='BLOCK':rm=0.0
        w[i]*=rm
        guard_rows.append({'ticker':code,'status':g.get('status'),'flags':g.get('flags'),'risk_multiplier':rm})
        bar=_last_bar(frames.get(code))
        current_alloc=pv*current.get(code,0.0)
        capd=capacity_assess(pv*w[i],current_alloc,adv,float(vol[i]*100),
                             price=bar.get('price') or rows[i].get('price'),high=bar.get('high'),low=bar.get('low'),
                             spread_bps=rows[i].get('spread_bps'),adv_limit_pct=adv_limit_pct)
        crm=max(0.0,min(1.0,float(capd.get('risk_multiplier',1.0) if capd.get('risk_multiplier') is not None else .5)))
        w[i]*=crm
        capd={'ticker':code,**capd,'baseline_weight_pct':round(float(baseline[i]*100),3),
              'pre_capacity_weight_pct':round(float((w[i]/crm if crm>0 else before)*100),3)}
        capacity_rows.append(capd)
        if w[i]>0:
            px=bar.get('price') or float(rows[i].get('price') or 1)
            synthetic_positions[code]=max(1,int((pv*w[i])/max(px,1e-9)))
    total=float(w.sum())
    if total>1:
        # Numerical safety only; constraints above should never increase total exposure.
        w=w/total;total=1.0
    cash=max(0.0,1.0-total)
    cov=rets[valid].cov().values*252
    port_vol=math.sqrt(max(float(w@cov@w),0))
    corr=rets[valid].corr().fillna(0)
    avg_corr=float(np.mean([corr.iloc[i,j] for i in range(len(valid)) for j in range(i+1,len(valid))])) if len(valid)>1 else 0
    outrows=[]
    for i,code in enumerate(valid):
        outrows.append({'ticker':code,'weight_pct':round(float(w[i]*100),3),'allocation':round(float(pv*w[i]),2),
                        'baseline_weight_pct':round(float(baseline[i]*100),3),'score':round(float(rows[i]['score']),6),
                        'volatility_pct':round(float(vol[i]*100),2),'capacity':capacity_rows[i]})
    return {'status':'OK','method':method,'portfolio_value':pv,'max_weight_pct':round(cap*100,2),
            'invested_weight_pct':round(total*100,2),'cash_weight_pct':round(cash*100,2),
            'cash_allocation':round(pv*cash,2),'annual_volatility_pct':round(port_vol*100,2),
            'avg_correlation':round(avg_corr,3),'rows':outrows,'liquidity_flags':liquidity_flags,
            'portfolio_guard':guard_rows,'capacity':capacity_summary(outrows,cash),
            'policy':'Paper challenger only. Caps, liquidity, portfolio risk and capacity may only reduce exposure; removed exposure remains cash.'}
