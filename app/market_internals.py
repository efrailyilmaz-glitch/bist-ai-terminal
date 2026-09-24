from __future__ import annotations
from typing import List
from .market_data import scan_codes

def market_internals(codes:List[str]):
    rows=scan_codes(codes[:100])
    n=len(rows)
    if not n:return {'status':'NO_DATA','count':0}
    def pct(cond):return round(100*sum(1 for r in rows if cond(r))/n,1)
    gainers=sorted(rows,key=lambda x:x.get('change',0),reverse=True)[:10]
    losers=sorted(rows,key=lambda x:x.get('change',0))[:10]
    liquid=sorted(rows,key=lambda x:x.get('volume_ratio',0),reverse=True)[:10]
    return {'status':'OK','count':n,
      'advance_pct':pct(lambda r:r.get('change',0)>0),'decline_pct':pct(lambda r:r.get('change',0)<0),
      'uptrend_pct':pct(lambda r:r.get('trend')=='YUKARI'),'strong_short_pct':pct(lambda r:r.get('short_score',0)>=70),
      'strong_long_pct':pct(lambda r:r.get('long_score',0)>=70),'breakout_pct':pct(lambda r:r.get('breakout20')),
      'bull_supertrend_pct':pct(lambda r:r.get('supertrend')=='BULLISH'),'bull_ichimoku_pct':pct(lambda r:r.get('ichimoku')=='BULLISH'),
      'above_ema20_pct':pct(lambda r:r.get('above_ema20')),'above_ema50_pct':pct(lambda r:r.get('above_ema50')),
      'above_ema200_pct':pct(lambda r:r.get('above_ema200')),'near_52w_high_pct':pct(lambda r:r.get('near_52w_high')),
      'median_rsi':round(sorted([r.get('rsi',50) for r in rows])[n//2],1),
      'gainers':gainers,'losers':losers,'volume_anomalies':liquid}
