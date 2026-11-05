"""V106 Execution Reality 2.0.
Unifies bar participation/slippage, BIST price-limit reality, optional licensed microstructure
and Trade Reality into one conservative paper-execution quality gate.
Missing evidence cannot improve the score.
"""
from __future__ import annotations
import math
from .execution_intelligence import execution_diagnostics
from .bist_execution_rules import quote_guard
from .microstructure import microstructure_guard

def _f(x,d=None):
    try:
        z=float(x);return z if math.isfinite(z) else d
    except Exception:return d

def evaluate_quote(q,qty,reference,side='BUY',base_slippage_bps=10,base_price=None,microstructure_snapshot=None,microstructure_result=None,trade_reality_result=None):
    ed=execution_diagnostics(q,qty,reference,base_slippage_bps,side)
    market=quote_guard(q,base_price)
    micro=microstructure_result if isinstance(microstructure_result,dict) else microstructure_guard(microstructure_snapshot) if microstructure_snapshot is not None else {'status':'UNKNOWN','score':0,'flags':['NO_MICROSTRUCTURE_DATA'],'risk_multiplier':1.0}
    reality=trade_reality_result or {'status':'NOT_RUN'}
    flags=[]
    flags += ['EXEC:'+str(x) for x in (ed.get('flags') or [])]
    flags += ['BIST:'+str(x) for x in (market.get('flags') or [])]
    if micro.get('status')!='GOOD':flags += ['MICRO:'+str(x) for x in (micro.get('flags') or [])]
    verdict=reality.get('verdict')
    if verdict=='UNFAVORABLE':flags.append('REALITY:UNFAVORABLE')
    elif verdict=='MARGINAL':flags.append('REALITY:MARGINAL')
    hard=(ed.get('status')=='BLOCK' or market.get('status')=='BLOCK' or micro.get('status')=='BAD' or verdict=='UNFAVORABLE')
    caution=(ed.get('status')=='CAUTION' or market.get('status')=='CAUTION' or micro.get('status') in {'CAUTION','UNKNOWN'} or verdict in {'MARGINAL',None} or reality.get('status') not in {'OK','NOT_APPLICABLE'})
    slip=max(0,_f(ed.get('effective_slippage_bps'),base_slippage_bps) or 0)
    participation=max(0,_f(ed.get('participation_rate_pct'),0) or 0)
    horizon=max(1,int(ed.get('execution_horizon_bars') or 1))
    quality=100
    quality-=min(35,slip*.35)
    quality-=min(25,participation*5)
    quality-=min(20,max(0,horizon-1)*10)
    if market.get('status')=='CAUTION':quality-=15
    if market.get('status')=='BLOCK':quality-=40
    if micro.get('status')=='CAUTION':quality-=10
    elif micro.get('status')=='BAD':quality-=30
    elif micro.get('status')=='UNKNOWN':quality-=5
    if verdict=='MARGINAL':quality-=12
    elif verdict=='UNFAVORABLE':quality-=35
    elif reality.get('status') not in {'OK','NOT_APPLICABLE'}:quality-=5
    quality=max(0,min(100,round(quality,1)))
    status='BLOCK' if hard or quality<30 else 'CAUTION' if caution or quality<65 else 'CLEAR'
    rm=0.0 if status=='BLOCK' else .65 if status=='CAUTION' else 1.0
    return {'status':status,'version':'106.0','quality_score':quality,'risk_multiplier':rm,'flags':list(dict.fromkeys(flags)),
            'execution':ed,'bist_market_rules':market,'microstructure':micro,'trade_reality':reality,
            'estimated_slippage_bps':ed.get('effective_slippage_bps'),'expected_fill_ratio_pct':ed.get('expected_fill_ratio_pct'),
            'execution_horizon_bars':ed.get('execution_horizon_bars'),'live_execution':False,
            'policy':'Paper/research execution gate only. Missing or adverse evidence can only reduce quality, worsen fills or block; it can never improve a fill or authorize a live order.'}

def snapshot(ticker,notional=100_000,side='BUY',base_slippage_bps=10):
    from .auto_paper import latest_quote,now_tr
    from .bist_execution_rules import previous_close
    from .microstructure_feed import latest_microstructure
    code=str(ticker).upper().replace('.IS','');q=latest_quote(code,now_tr())
    if not q:return {'ticker':code,'status':'NO_QUOTE','live_execution':False}
    px=_f(q.get('close'),0) or 0
    qty=max(0,int(float(notional)/px)) if px>0 else 0
    micro=latest_microstructure(code)
    mg=micro.get('guard') if isinstance(micro,dict) else None
    r=evaluate_quote(q,qty,px,side,base_slippage_bps,base_price=previous_close(code),microstructure_result=mg)
    return {'ticker':code,'reference_price':px,'notional':float(notional),'quantity':qty,**r}
