"""Forward-only champion/challenger governance.
Ranks only prospective paper results. Historical backtests cannot self-promote.
"""
from __future__ import annotations
import math

def _finite(x,default=0.0):
    try:
        x=float(x)
        return x if math.isfinite(x) else default
    except Exception:return default

def conservative_score(metrics,days=0):
    """Shrink small samples and penalize drawdown/costs.
    This score is for paper-tournament ordering only.
    """
    trades=max(0,int(metrics.get('closed_trades') or 0))
    ret=_finite(metrics.get('return_pct'));dd=max(0,_finite(metrics.get('max_drawdown_pct'),100))
    pf=metrics.get('profit_factor')
    pf=_finite(pf,1.0) if pf is not None else 1.0
    fees=max(0,_finite(metrics.get('fees_paid')))
    sample=min(1.0,trades/60.0)*min(1.0,max(0,days)/120.0)
    edge=ret-1.35*dd+4.0*(pf-1.0)
    fee_penalty=min(8.0,fees/10000.0)
    return round((edge-fee_penalty)*sample,4)

def rank_forward_bots(rows,started_days,benchmark_return=None):
    out=[]
    for row in rows or []:
        m=row.get('metrics') or {}
        score=conservative_score(m,started_days)
        reasons=[]
        if started_days<90:reasons.append('MIN_90_DAYS')
        if int(m.get('closed_trades') or 0)<30:reasons.append('MIN_30_TRADES')
        if _finite(m.get('max_drawdown_pct'),999)>8:reasons.append('DRAWDOWN')
        pf=m.get('profit_factor')
        if pf is None or _finite(pf)<1.2:reasons.append('PROFIT_FACTOR')
        if isinstance(benchmark_return,(int,float)) and _finite(m.get('return_pct'),-999)<=benchmark_return:reasons.append('BENCHMARK')
        out.append({'id':row.get('id'),'name':row.get('name'),'score':score,
                    'status':'ELIGIBLE' if not reasons else 'OBSERVE','reasons':reasons})
    out.sort(key=lambda x:(x['status']!='ELIGIBLE',-x['score'],x['id'] or ''))
    return out

def meta_decision(ranking,current_champion=None):
    eligible=[r for r in ranking if r.get('status')=='ELIGIBLE']
    if not eligible:return {'action':'HOLD','champion':current_champion,'reason':'NO_ELIGIBLE_CHALLENGER'}
    best=eligible[0]
    if not current_champion:return {'action':'NOMINATE','champion':best['id'],'reason':'FIRST_ELIGIBLE'}
    incumbent=next((x for x in eligible if x['id']==current_champion),None)
    if incumbent is None:return {'action':'NOMINATE','champion':best['id'],'reason':'INCUMBENT_NOT_ELIGIBLE'}
    # Hysteresis prevents churn. Challenger must beat incumbent by a material margin.
    if best['id']!=current_champion and best['score']>=incumbent['score']+2.5:
        return {'action':'NOMINATE','champion':best['id'],'reason':'CHALLENGER_MARGIN'}
    return {'action':'HOLD','champion':current_champion,'reason':'HYSTERESIS'}
