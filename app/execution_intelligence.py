"""Execution realism for delayed-bar paper trading.
Estimates short-horizon implementation cost from bar range, participation and liquidity.
It is intentionally conservative and can only worsen simulated fills or block entries.
"""
from __future__ import annotations
import math

def _f(x,default=None):
    try:
        z=float(x)
        return z if math.isfinite(z) else default
    except Exception:return default

def execution_diagnostics(q,qty,reference,base_slippage_bps=10,side='BUY'):
    px=_f(reference);vol=_f((q or {}).get('volume'));hi=_f((q or {}).get('high'));lo=_f((q or {}).get('low'))
    if not px or px<=0 or not vol or vol<=0 or not hi or not lo or hi<lo:
        return {'status':'UNKNOWN','effective_slippage_bps':float(base_slippage_bps),'risk_multiplier':.75,
                'flags':['EXECUTION_DATA_MISSING']}
    qty=max(0,int(qty or 0));participation=qty/vol if vol>0 else 1.0
    range_bps=max(0,(hi-lo)/px*10000)
    base=max(0,float(base_slippage_bps))
    # Conservative square-root participation penalty using only observed completed-bar data.
    impact_bps=range_bps*0.35*math.sqrt(max(0,participation))
    vol_penalty=max(0,range_bps-120)*0.08
    eff=base+impact_bps+vol_penalty
    flags=[];status='CLEAR';rm=1.0
    if participation>.02:flags.append('HIGH_PARTICIPATION')
    if participation>.05:flags.append('EXTREME_PARTICIPATION')
    if range_bps>250:flags.append('HIGH_INTRABAR_RANGE')
    if eff>45:flags.append('HIGH_EXPECTED_SLIPPAGE')
    if eff>80 or participation>.05:
        status='BLOCK';rm=0.0
    elif eff>35 or participation>.02 or range_bps>250:
        status='CAUTION';rm=.65
    return {'status':status,'effective_slippage_bps':round(eff,2),'base_slippage_bps':round(base,2),
            'impact_bps':round(impact_bps,2),'range_bps':round(range_bps,2),
            'participation_rate_pct':round(participation*100,3),'risk_multiplier':rm,'flags':flags,
            'note':'Delayed-bar paper estimate only. Higher participation/range worsens simulated execution; it never improves fills.'}

def slippage_price(reference,side,effective_slippage_bps):
    px=float(reference);bps=max(0,float(effective_slippage_bps))
    buy=str(side).upper() in {'BUY','COVER'}
    return px*(1+(1 if buy else -1)*bps/10000)
