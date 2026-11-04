"""V68 Borsa Istanbul execution-reality guard for ordinary equity paper trading.
Official-source policy snapshot (verified 2026-11-04):
- current share price-margin application: 10% for the principal share markets covered here,
- share circuit breaker: downside-only 5%,
- circuit-breaker call auction: 10 minutes, matching: 2 minutes,
- closing auction price band: +/-3% around the pre-closing last trade.
This module does not infer that an auction actually occurred without observable evidence.
"""
from __future__ import annotations
import math,time,threading

_LOCK=threading.Lock();_CACHE={}
PRICE_MARGIN_PCT=10.0
CIRCUIT_BREAKER_DOWN_PCT=5.0
CIRCUIT_CALL_MINUTES=10
CIRCUIT_MATCH_MINUTES=2
CLOSING_AUCTION_BAND_PCT=3.0
SOURCE='Borsa Istanbul Pay Piyasasi - Piyasa Isleyisi / Pazarlar, verified 2026-11-04'

def _f(x,default=None):
    try:
        z=float(x);return z if math.isfinite(z) else default
    except Exception:return default

def official_policy():
    return {'status':'VERIFIED','instrument_scope':'ORDINARY_EQUITY_PAPER_MODEL',
            'price_margin_pct':PRICE_MARGIN_PCT,'circuit_breaker_down_pct':CIRCUIT_BREAKER_DOWN_PCT,
            'circuit_call_minutes':CIRCUIT_CALL_MINUTES,'circuit_match_minutes':CIRCUIT_MATCH_MINUTES,
            'closing_auction_band_pct':CLOSING_AUCTION_BAND_PCT,'source':SOURCE,
            'limitations':['Exact tick-size rounding is not simulated here.','Special instruments/free-price cases require separate metadata.']}

def previous_close(ticker,ttl=600):
    code=str(ticker).upper().replace('.IS','');now=time.time()
    with _LOCK:
        hit=_CACHE.get(code)
        if hit and now-hit[0]<ttl:return hit[1]
    try:
        from .market_data import yahoo_rows
        rows=(yahoo_rows(code,period='5d',interval='1d').get('candles') or [])
        px=float(rows[-2]['close']) if len(rows)>=2 else None
    except Exception:px=None
    with _LOCK:_CACHE[code]=(now,px)
    return px

def price_limits(base_price,margin_pct=PRICE_MARGIN_PCT):
    base=_f(base_price)
    if not base or base<=0:return {'status':'UNKNOWN'}
    m=max(0,float(margin_pct))/100
    return {'status':'OK','base_price':base,'lower_limit':base*(1-m),'upper_limit':base*(1+m),'margin_pct':float(margin_pct)}

def quote_guard(q,base_price=None):
    base=_f(base_price)
    if base is None:base=_f((q or {}).get('previous_close'))
    if not base or base<=0:
        return {'status':'CAUTION','risk_multiplier':.75,'flags':['BASE_PRICE_UNKNOWN'],'policy':official_policy()}
    lim=price_limits(base)
    lo=_f((q or {}).get('low'));hi=_f((q or {}).get('high'));op=_f((q or {}).get('open'));cl=_f((q or {}).get('close'))
    if any(x is None for x in [lo,hi,op,cl]):
        return {'status':'BLOCK','risk_multiplier':0.0,'flags':['PRICE_BAR_INCOMPLETE'],'limits':lim,'policy':official_policy()}
    eps=base*.001
    flags=[];status='PASS';rm=1.0
    if lo<lim['lower_limit']-eps or hi>lim['upper_limit']+eps or op<lim['lower_limit']-eps or op>lim['upper_limit']+eps or cl<lim['lower_limit']-eps or cl>lim['upper_limit']+eps:
        return {'status':'BLOCK','risk_multiplier':0.0,'flags':['PRICE_LIMIT_VIOLATION_OR_CORPORATE_ACTION'],
                'limits':lim,'policy':official_policy()}
    drop=(cl/base-1)*100
    if drop<=-CIRCUIT_BREAKER_DOWN_PCT:
        flags.append('CIRCUIT_BREAKER_ZONE')
        status='CAUTION';rm=min(rm,.5)
    lower_lock=lo<=lim['lower_limit']+eps and cl<=lim['lower_limit']+eps
    upper_lock=hi>=lim['upper_limit']-eps and cl>=lim['upper_limit']-eps
    if lower_lock:flags.append('LOWER_LIMIT_LOCK_RISK')
    if upper_lock:flags.append('UPPER_LIMIT_LOCK_RISK')
    if lower_lock or upper_lock:
        status='CAUTION';rm=min(rm,.5)
    return {'status':status,'risk_multiplier':rm,'flags':flags,'limits':lim,'drop_from_base_pct':round(drop,3),
            'lower_lock_risk':lower_lock,'upper_lock_risk':upper_lock,'policy':official_policy()}

def protective_fill(reference_stop,q,side,base_price=None):
    """Return a conservative paper protective-exit decision.
    When a bar is visibly locked at the adverse daily price limit, no liquidity is assumed.
    """
    g=quote_guard(q,base_price)
    if g.get('status')=='BLOCK':
        return {'status':'DATA_BLOCK','guard':g}
    stop=_f(reference_stop);op=_f((q or {}).get('open'))
    if not stop or not op:return {'status':'DATA_BLOCK','guard':g}
    long_exit=str(side).upper()=='SELL'
    if long_exit and g.get('lower_lock_risk'):
        return {'status':'NO_FILL_LIMIT_LOCK','guard':g,'reason':'LOWER_LIMIT_LOCK_NO_LIQUIDITY_ASSUMED'}
    if not long_exit and g.get('upper_lock_risk'):
        return {'status':'NO_FILL_LIMIT_LOCK','guard':g,'reason':'UPPER_LIMIT_LOCK_NO_LIQUIDITY_ASSUMED'}
    px=min(op,stop) if long_exit else max(op,stop)
    lim=g.get('limits') or {}
    if long_exit and lim.get('lower_limit') is not None:px=max(px,float(lim['lower_limit']))
    if not long_exit and lim.get('upper_limit') is not None:px=min(px,float(lim['upper_limit']))
    return {'status':'FILL','price':px,'guard':g,
            'gap_through_stop':bool(op<stop if long_exit else op>stop)}
