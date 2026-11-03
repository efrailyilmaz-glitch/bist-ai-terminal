"""V60 hard promotion governance for XS prospective challengers.
Backtest/lab results can never satisfy these gates. Promotion remains review-only.
"""
from __future__ import annotations
import math
from .xs_paper import verify_lineage_ledger

def _f(x,default=0.0):
    try:
        z=float(x)
        return z if math.isfinite(z) else default
    except Exception:return default

def evaluate(history,days,lineage_status=None,min_days=90,min_rebalances=12,max_drawdown_pct=8.0,
             max_avg_turnover_pct=70.0,max_cost_pct_of_capital=3.0,min_excess_pct=0.0):
    p=(history or {}).get('portfolio') or {}
    rebs=(history or {}).get('rebalances') or []
    curve=list(reversed((history or {}).get('curve') or []))
    capital=max(1.0,_f(p.get('capital'),1.0))
    equity=_f(p.get('last_equity'),capital)
    ret=(equity/capital-1)*100
    excess=_f(curve[-1].get('excess_pct')) if curve else 0.0
    maxdd=max([abs(_f(x.get('drawdown_pct'))) for x in curve],default=0.0)
    avg_turnover=sum(_f(x.get('turnover_pct')) for x in rebs)/len(rebs) if rebs else 0.0
    costs=sum(_f(x.get('cost')) for x in rebs)
    cost_pct=costs/capital*100
    linked=[x for x in rebs if x.get('model_registry_id') and x.get('model_fingerprint')]
    reproducibility_pct=(len(linked)/len(rebs)*100) if rebs else 0.0
    lineage_status=lineage_status or verify_lineage_ledger().get('status')
    reasons=[]
    if int(days)<int(min_days):reasons.append('MIN_90_FORWARD_DAYS')
    if len(rebs)<int(min_rebalances):reasons.append('MIN_12_REBALANCES')
    if excess<=float(min_excess_pct):reasons.append('NO_POSITIVE_BENCHMARK_EXCESS')
    if maxdd>float(max_drawdown_pct):reasons.append('MAX_DRAWDOWN_ABOVE_8')
    if avg_turnover>float(max_avg_turnover_pct):reasons.append('AVERAGE_TURNOVER_TOO_HIGH')
    if cost_pct>float(max_cost_pct_of_capital):reasons.append('COST_BURDEN_TOO_HIGH')
    if rebs and reproducibility_pct<100:reasons.append('MODEL_REPRODUCIBILITY_INCOMPLETE')
    if lineage_status!='PASS':reasons.append('LINEAGE_INTEGRITY_FAIL')
    status='PROMOTION_REVIEW' if not reasons else ('BLOCK' if 'LINEAGE_INTEGRITY_FAIL' in reasons else 'OBSERVE')
    return {'status':status,'reasons':reasons,'metrics':{
        'forward_days':int(days),'rebalance_count':len(rebs),'return_pct':round(ret,4),'excess_pct':round(excess,4),
        'max_drawdown_pct':round(maxdd,4),'avg_turnover_pct':round(avg_turnover,2),
        'costs_paid':round(costs,2),'cost_pct_of_capital':round(cost_pct,4),
        'model_reproducibility_pct':round(reproducibility_pct,1),'lineage_status':lineage_status},
        'policy':'Promotion review only. This gate never enables live execution.'}
