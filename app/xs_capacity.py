"""V66 portfolio-level capacity and market-impact diagnostics for XS paper allocation.
Conservative: diagnostics can only reduce/block target exposure. Missing data never boosts risk.
"""
from __future__ import annotations
import math

def _f(x,default=None):
    try:
        z=float(x)
        return z if math.isfinite(z) else default
    except Exception:return default

def assess(allocation,current_allocation,value_turnover,annual_vol_pct,price=None,high=None,low=None,spread_bps=None,
           adv_limit_pct=1.0,max_horizon_days=2,base_impact_bps=10):
    alloc=max(0,_f(allocation,0) or 0);cur=max(0,_f(current_allocation,0) or 0)
    trade=abs(alloc-cur);adv=_f(value_turnover,0) or 0
    if trade<=0:
        return {'status':'CLEAR','risk_multiplier':1.0,'trade_notional':0.0,'execution_horizon_days':0,
                'effective_impact_bps':0.0,'flags':[]}
    if adv<=0:
        return {'status':'UNKNOWN','risk_multiplier':.5,'trade_notional':round(trade,2),
                'execution_horizon_days':None,'effective_impact_bps':None,'flags':['ADV_UNKNOWN']}
    limit=max(.001,min(float(adv_limit_pct)/100,.10))
    daily_capacity=adv*limit
    horizon=max(1,int(math.ceil(trade/max(daily_capacity,1))))
    participation=trade/adv
    px=_f(price);hi=_f(high);lo=_f(low)
    if px and px>0 and hi and lo and hi>=lo:
        range_bps=max(0,(hi-lo)/px*10000)
    else:
        daily_vol=max(0,(_f(annual_vol_pct,0) or 0)/math.sqrt(252))
        range_bps=daily_vol*100
    share=min(participation,limit)
    quadratic=18.0*(share/limit)**2
    sqrt_impact=range_bps*.35*math.sqrt(max(0,participation))
    spread=max(0,_f(spread_bps,0) or 0)
    vol_penalty=max(0,(_f(annual_vol_pct,0) or 0)-60)*.20
    eff=max(0,float(base_impact_bps))+quadratic+sqrt_impact+spread/2+vol_penalty
    flags=[];status='CLEAR';rm=1.0
    if participation>.02:flags.append('HIGH_ADV_PARTICIPATION')
    if participation>limit:flags.append('ADV_LIMIT_EXCEEDED')
    if horizon>1:flags.append('MULTI_DAY_EXECUTION_REQUIRED')
    if horizon>max_horizon_days:flags.append('EXECUTION_HORIZON_TOO_LONG')
    if spread>35:flags.append('WIDE_SPREAD')
    if (_f(annual_vol_pct,0) or 0)>70:flags.append('HIGH_VOLATILITY')
    if eff>45:flags.append('HIGH_EXPECTED_IMPACT')
    if horizon>max_horizon_days or eff>80 or participation>.05:
        status='BLOCK';rm=0.0
    elif flags:
        status='CAUTION'
        rm=.65 if horizon>1 or eff>35 else .8
    return {'status':status,'risk_multiplier':rm,'trade_notional':round(trade,2),
            'adv_value':round(adv,2),'participation_pct':round(participation*100,3),
            'daily_capacity':round(daily_capacity,2),'execution_horizon_days':horizon,
            'range_bps':round(range_bps,2),'spread_bps':round(spread,2),
            'effective_impact_bps':round(eff,2),'flags':flags,
            'note':'Paper capacity estimate. ADV, volatility, range, spread and execution horizon can only reduce or block exposure.'}

def portfolio_summary(rows,cash_weight):
    ds=[x.get('capacity') or {} for x in rows or []]
    blocked=sum(1 for x in ds if x.get('status')=='BLOCK')
    caution=sum(1 for x in ds if x.get('status') in {'CAUTION','UNKNOWN'})
    impacts=[_f(x.get('effective_impact_bps')) for x in ds]
    impacts=[x for x in impacts if x is not None]
    horizons=[x.get('execution_horizon_days') for x in ds if isinstance(x.get('execution_horizon_days'),int)]
    return {'blocked_names':blocked,'caution_names':caution,'cash_weight_pct':round(float(cash_weight)*100,2),
            'max_effective_impact_bps':None if not impacts else round(max(impacts),2),
            'max_execution_horizon_days':None if not horizons else max(horizons),
            'status':'BLOCK' if blocked else ('CAUTION' if caution else 'PASS')}
