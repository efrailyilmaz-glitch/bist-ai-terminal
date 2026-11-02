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

def execution_diagnostics(q,qty,reference,base_slippage_bps=10,side='BUY',volume_limit=.025,impact_at_limit_bps=18):
    px=_f(reference);vol=_f((q or {}).get('volume'));hi=_f((q or {}).get('high'));lo=_f((q or {}).get('low'))
    if not px or px<=0 or not vol or vol<=0 or not hi or not lo or hi<lo:
        return {'status':'UNKNOWN','effective_slippage_bps':float(base_slippage_bps),'risk_multiplier':.75,
                'flags':['EXECUTION_DATA_MISSING']}
    qty=max(0,int(qty or 0));participation=qty/vol if vol>0 else 1.0
    range_bps=max(0,(hi-lo)/px*10000)
    base=max(0,float(base_slippage_bps))
    # Existing range-aware square-root impact.
    impact_bps=range_bps*0.35*math.sqrt(max(0,participation))
    # V44 volume-share impact: quadratic participation penalty, inspired by common
    # execution models. Constants are an explicit conservative policy, not a market truth.
    volume_limit=max(.001,min(float(volume_limit),.10))
    share=min(participation,volume_limit)
    volume_share_impact_bps=max(0,float(impact_at_limit_bps))*(share/volume_limit)**2
    max_fill_qty=max(1,int(vol*volume_limit))
    fill_ratio=1.0 if qty<=0 else min(1.0,max_fill_qty/max(1,qty))
    horizon_bars=1 if qty<=max_fill_qty else int(math.ceil(qty/max_fill_qty))
    bid=_f((q or {}).get('bid'));ask=_f((q or {}).get('ask'))
    spread_bps=((ask-bid)/px*10000) if bid and ask and ask>=bid and bid>0 else None
    spread_penalty=(spread_bps/2) if spread_bps is not None else 0.0
    vol_penalty=max(0,range_bps-120)*0.08
    eff=base+impact_bps+volume_share_impact_bps+spread_penalty+vol_penalty
    flags=[];status='CLEAR';rm=1.0
    if participation>.02:flags.append('HIGH_PARTICIPATION')
    if participation>volume_limit:flags.append('VOLUME_SHARE_LIMIT_EXCEEDED')
    if horizon_bars>1:flags.append('MULTI_BAR_EXECUTION_REQUIRED')
    if spread_bps is not None and spread_bps>35:flags.append('WIDE_SPREAD')
    if participation>.05:flags.append('EXTREME_PARTICIPATION')
    if range_bps>250:flags.append('HIGH_INTRABAR_RANGE')
    if eff>45:flags.append('HIGH_EXPECTED_SLIPPAGE')
    if eff>80 or participation>.05 or horizon_bars>2:
        status='BLOCK';rm=0.0
    elif eff>35 or participation>.02 or range_bps>250 or horizon_bars>1 or (spread_bps is not None and spread_bps>35):
        status='CAUTION';rm=.65
    return {'status':status,'effective_slippage_bps':round(eff,2),'base_slippage_bps':round(base,2),
            'impact_bps':round(impact_bps,2),'volume_share_impact_bps':round(volume_share_impact_bps,2),
            'spread_bps':None if spread_bps is None else round(spread_bps,2),'range_bps':round(range_bps,2),
            'participation_rate_pct':round(participation*100,3),'volume_limit_pct':round(volume_limit*100,2),
            'max_fill_qty_per_bar':max_fill_qty,'expected_fill_ratio_pct':round(fill_ratio*100,1),
            'execution_horizon_bars':horizon_bars,'risk_multiplier':rm,'flags':flags,
            'note':'Delayed-bar paper estimate only. Range, quadratic volume-share impact and observed spread can only worsen execution; never improve it.'}

def slippage_price(reference,side,effective_slippage_bps):
    px=float(reference);bps=max(0,float(effective_slippage_bps))
    buy=str(side).upper() in {'BUY','COVER'}
    return px*(1+(1 if buy else -1)*bps/10000)
