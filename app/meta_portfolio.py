"""Forward-only meta-portfolio allocator.
Produces a paper allocation policy across eligible robot families with explicit cash.
Historical backtests never enter the weighting function.
"""
from __future__ import annotations
import math

TREND={'baseline','alphatrend','ott','tott','tsmomentum','donchian55','lowvolbreak','defmom','qqe_ssl_wae','kama_regime','regimemeta','codex','codexpro'}
MEANREV={'meanrev'}
MOMENTUM={'momentum','relative_momentum','tsmomentum','defmom','qqe_ssl_wae'}

def arena_regime(scan,benchmark):
    breadth=scan.get('breadth_pct') if isinstance(scan,dict) else None
    br=(benchmark or {}).get('cash_adjusted_pct')
    if isinstance(breadth,(int,float)) and breadth<35:return 'RISK_OFF'
    if isinstance(br,(int,float)) and br<-6:return 'RISK_OFF'
    if isinstance(breadth,(int,float)) and breadth>=60 and (not isinstance(br,(int,float)) or br>=0):return 'BULL_TREND'
    if isinstance(breadth,(int,float)) and breadth<=45:return 'RANGE_WEAK'
    return 'RANGE'

def _suitability(bot_id,regime):
    b=str(bot_id)
    if regime=='RISK_OFF':
        return .15
    if regime=='BULL_TREND':
        return 1.0 if b in TREND or b in MOMENTUM else .45
    if regime=='RANGE_WEAK':
        return 1.0 if b in MEANREV else .45 if b in {'kama_regime','regimemeta'} else .25
    return .8 if b in {'kama_regime','regimemeta'} else .65 if b in MEANREV else .55

def allocate(rows,ranking,regime,max_bot_weight=.25):
    rows_by={r.get('id'):r for r in rows or []};rank_by={r.get('id'):r for r in ranking or []}
    cash_floor={'RISK_OFF':.70,'RANGE_WEAK':.45,'RANGE':.35,'BULL_TREND':.20}.get(regime,.35)
    investable=1-cash_floor;candidates=[]
    for bid,rk in rank_by.items():
        row=rows_by.get(bid) or {};decay=(row.get('decay') or {}).get('status')
        if rk.get('status')!='ELIGIBLE' or decay=='DECAY':continue
        score=max(0,float(rk.get('score') or 0))
        suit=_suitability(bid,regime)
        confidence=.65 if decay=='WATCH' else 1.0
        raw=max(.01,(1+score/10))*suit*confidence
        candidates.append({'id':bid,'name':row.get('name',bid),'raw':raw,'suitability':suit,'decay':decay})
    if not candidates:return {'regime':regime,'cash_weight_pct':100.0,'allocations':[],'status':'ALL_CASH','reason':'NO_ELIGIBLE_FORWARD_BOTS'}
    # Iterative capped normalization; prevents a single robot/family dominating capital.
    remain=investable;active={x['id']:x for x in candidates};weights={}
    while active and remain>1e-9:
        total=sum(x['raw'] for x in active.values()) or 1
        capped=[];proposed={}
        for bid,x in active.items():
            w=remain*x['raw']/total
            if w>=max_bot_weight:
                weights[bid]=max_bot_weight;remain-=max_bot_weight;capped.append(bid)
            else:proposed[bid]=w
        if not capped:
            weights.update(proposed);remain=0;break
        for bid in capped:active.pop(bid,None)
        if sum(weights.values())>=investable-1e-9:break
    used=sum(weights.values())
    # Any unusable investable capital stays cash rather than being forced into weak candidates.
    cash=1-used
    out=[]
    for x in candidates:
        w=weights.get(x['id'],0)
        if w<=0:continue
        out.append({'id':x['id'],'name':x['name'],'weight_pct':round(w*100,2),
                    'suitability':round(x['suitability'],2),'decay':x['decay']})
    out.sort(key=lambda x:-x['weight_pct'])
    return {'regime':regime,'cash_weight_pct':round(cash*100,2),'invested_weight_pct':round(used*100,2),
            'allocations':out,'status':'OK',
            'constraints':{'max_bot_weight_pct':round(max_bot_weight*100,1),'cash_floor_pct':round(cash_floor*100,1)},
            'note':'Forward-paper allocator only. No historical backtest enters weights; weak/decaying robots cannot force capital deployment.'}
