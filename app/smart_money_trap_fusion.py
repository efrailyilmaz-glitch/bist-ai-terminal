"""V99 Smart Money + Trap Defense fusion.
Combines OHLCV accumulation/markup proxies with deception-risk heuristics.
Never claims a manipulator/actor is present and never authorizes execution.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from .smart_money_engine import smart_money_snapshot,smart_money_radar,_frame
from .trap_defense import assess_traps

def snapshot(ticker):
    code=ticker.upper().replace('.IS','')
    sm=smart_money_snapshot(code,calibrate=True)
    if sm.get('status')!='OK':return {'ticker':code,'status':'NO_DATA'}
    df=_frame(code,'5y')
    trap=assess_traps(df[['Open','High','Low','Close','Volume']] if df is not None else None)
    acc=float(sm.get('accumulation_probability') or 0);markup=float(sm.get('markup_probability') or 0)
    dist=float(sm.get('distribution_risk') or 0);exit_risk=float(sm.get('exit_risk') or 0);ts=float(trap.get('score') or 100)
    bullish=acc>=72 and markup>=68 and dist<65
    clean=trap.get('status')=='CLEAR' and ts<28
    if bullish and clean:
        state='CLEAN_ACCUMULATION_WATCH'
    elif bullish and not clean:
        state='BULLISH_CONFLICT_TRAP_RISK'
    elif dist>=72 and trap.get('status') in {'WAIT','BLOCK'}:
        state='DISTRIBUTION_AND_TRAP_RISK'
    elif dist>=72:
        state='DISTRIBUTION_WATCH'
    else:
        state='NEUTRAL'
    fusion=max(0,min(100,.40*acc+.30*markup-.20*dist-.35*ts))
    risk=max(0,min(100,.45*dist+.30*exit_risk+.45*ts))
    reasons=list(sm.get('reasons') or [])
    if trap.get('status')!='CLEAR':reasons+=['Trap Defense '+str(trap.get('status'))+' · '+str(trap.get('score'))+'/100']
    return {'ticker':code,'status':'OK','state':state,'fusion_score':round(fusion,1),'risk_score':round(risk,1),
            'smart_money':sm,'trap_defense':trap,'reasons':reasons[:12],
            'research_action':'WATCH_CLEAN_SETUP' if state=='CLEAN_ACCUMULATION_WATCH' else 'AVOID_CHASING' if 'TRAP_RISK' in state else 'MONITOR',
            'live_execution':False,
            'warning':'Smart-money and trap labels are OHLCV behaviour proxies only. They do not identify a manipulator, market maker, broker or specific actor.'}

def radar(limit=20):
    base=smart_money_radar(limit=max(20,min(int(limit)*2,50)),universe_limit=0).get('rows') or []
    rows=[]
    with ThreadPoolExecutor(max_workers=5) as pool:
        fut=[pool.submit(snapshot,x.get('ticker')) for x in base if x.get('ticker')]
        for q in as_completed(fut):
            try:
                r=q.result()
                if r.get('status')=='OK':rows.append(r)
            except Exception:pass
    priority={'CLEAN_ACCUMULATION_WATCH':0,'BULLISH_CONFLICT_TRAP_RISK':1,'DISTRIBUTION_AND_TRAP_RISK':2,'DISTRIBUTION_WATCH':3,'NEUTRAL':4}
    rows.sort(key=lambda x:(priority.get(x['state'],9),-x['fusion_score'],x['risk_score']))
    return {'status':'OK','version':'99.0','rows':rows[:max(5,min(int(limit),50))],
            'clean_count':sum(1 for x in rows if x['state']=='CLEAN_ACCUMULATION_WATCH'),
            'conflict_count':sum(1 for x in rows if x['state']=='BULLISH_CONFLICT_TRAP_RISK'),
            'live_execution':False,
            'note':'Fusion prioritizes clean accumulation candidates and explicitly separates bullish-looking setups with trap risk.'}
