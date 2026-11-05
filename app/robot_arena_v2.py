"""V105 Robot Arena 2.0 forward scorecard.
Ranks every configured robot on the same prospective arena without dropping losers/non-traders.
The score is descriptive governance for paper research only.
"""
from __future__ import annotations
import math

FAMILIES={
 'baseline':'BASELINE','alphatrend':'TREND','ott':'TREND','tott':'TREND','momentum':'MOMENTUM',
 'tsmomentum':'MOMENTUM','donchian55':'BREAKOUT','meanrev':'MEAN_REVERSION','lowvolbreak':'BREAKOUT',
 'defmom':'DEFENSIVE_MOMENTUM','codex':'MULTI_FACTOR','codexpro':'ENSEMBLE','qqe_ssl_wae':'INDICATOR_FUSION',
 'kama_regime':'ADAPTIVE_TREND','regimemeta':'REGIME_META'
}

def _f(x,d=0.0):
    try:
        z=float(x);return z if math.isfinite(z) else d
    except Exception:return d

def score(rows,benchmark_return=None,days=0):
    bench=_f(benchmark_return,0.0) if isinstance(benchmark_return,(int,float)) else 0.0
    out=[]
    for r in rows or []:
        m=r.get('metrics') or {};decay=(r.get('decay') or {}).get('status') or 'UNKNOWN'
        ret=_f(m.get('return_pct'));excess=ret-bench
        dd=max(0,_f(m.get('max_drawdown_pct'),100));trades=max(0,int(m.get('closed_trades') or 0))
        pf=m.get('profit_factor');pfv=_f(pf,1.0) if pf is not None else 1.0
        wr=m.get('win_rate_pct');wrv=_f(wr,50.0) if wr is not None else 50.0
        maturity=min(1.0,trades/40.0)*min(1.0,max(0,int(days))/90.0)
        decay_penalty=8.0 if decay=='DECAY' else 3.0 if decay=='WATCH' else 0.0
        raw=excess*1.8-dd*1.25+max(-4,min(8,(pfv-1)*4))+max(-2,min(2,(wrv-50)/15))-decay_penalty
        score=max(-100,min(100,raw*maturity))
        family=FAMILIES.get(str(r.get('id')),'OTHER')
        out.append({'id':r.get('id'),'name':r.get('name'),'family':family,'score':round(score,3),
                    'return_pct':round(ret,3),'benchmark_excess_pct':round(excess,3),'max_drawdown_pct':round(dd,3),
                    'closed_trades':trades,'profit_factor':None if pf is None else round(pfv,3),
                    'win_rate_pct':None if wr is None else round(wrv,2),'decay':decay,
                    'maturity_pct':round(maturity*100,1),'eligible':(r.get('promotion') or {}).get('status')=='CHALLENGER_ELIGIBLE'})
    # Keep all configured bots, including non-traders and losers; sorting never filters.
    out.sort(key=lambda x:(-x['score'],x['max_drawdown_pct'],x['id'] or ''))
    families={}
    for x in out:
        z=families.setdefault(x['family'],{'family':x['family'],'bots':0,'best_score':-1e18,'best_bot':None,'mean_score':0.0})
        z['bots']+=1;z['mean_score']+=x['score']
        if x['score']>z['best_score']:z['best_score']=x['score'];z['best_bot']=x['id']
    family_rows=[]
    for z in families.values():
        z['mean_score']=round(z['mean_score']/max(1,z['bots']),3);z['best_score']=round(z['best_score'],3);family_rows.append(z)
    family_rows.sort(key=lambda x:-x['mean_score'])
    leader=out[0] if out else None
    return {'status':'OK','version':'105.0','days':int(days),'benchmark_return_pct':benchmark_return,
            'rows':out,'families':family_rows,'leader':leader,
            'survivor_bias_policy':'All configured robots remain in the table even with zero trades, losses or decay. No failed robot is silently removed.',
            'live_execution':False,
            'policy':'Equal-capital/equal-cost prospective paper comparison only. Score cannot promote a robot to live execution.'}
