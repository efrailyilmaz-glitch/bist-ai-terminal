"""Forward-only strategy decay diagnostics.
Uses only realised paper trades/equity observations. Historical backtests are excluded.
"""
from __future__ import annotations
import math,numpy as np

def _stats(pnls):
    x=[float(v) for v in pnls if isinstance(v,(int,float)) and math.isfinite(float(v))]
    if not x:return {'n':0,'expectancy':None,'win_rate':None,'profit_factor':None}
    gains=sum(v for v in x if v>0);loss=-sum(v for v in x if v<0)
    return {'n':len(x),'expectancy':sum(x)/len(x),'win_rate':sum(v>0 for v in x)/len(x)*100,
            'profit_factor':gains/loss if loss>0 else (999.0 if gains>0 else 0.0)}

def detect_decay(bot,min_trades=24,window=12):
    exits=[o for o in reversed(bot.get('orders') or []) if isinstance(o.get('pnl'),(int,float))]
    pnls=[float(o['pnl']) for o in exits]
    if len(pnls)<min_trades:
        return {'status':'INSUFFICIENT','closed_trades':len(pnls),'flags':['MIN_FORWARD_TRADES'],
                'note':'Forward paper evidence only; no historical backtest is used.'}
    w=max(8,min(int(window),len(pnls)//2))
    prior=_stats(pnls[-2*w:-w]);recent=_stats(pnls[-w:])
    flags=[];score=0
    pe=prior['expectancy'] or 0;re=recent['expectancy'] or 0
    if pe>0 and re<0:flags.append('EXPECTANCY_SIGN_FLIP');score+=35
    elif pe>0 and re<pe*.35:flags.append('EXPECTANCY_COLLAPSE');score+=20
    ppf=prior['profit_factor'];rpf=recent['profit_factor']
    if isinstance(ppf,(int,float)) and isinstance(rpf,(int,float)) and ppf>=1.2 and rpf<.9:
        flags.append('PROFIT_FACTOR_DECAY');score+=25
    if recent['win_rate'] is not None and prior['win_rate'] is not None and recent['win_rate']+20<prior['win_rate']:
        flags.append('WIN_RATE_DECAY');score+=15
    curve=[x for x in (bot.get('curve') or []) if isinstance(x.get('equity'),(int,float))]
    if len(curve)>=40:
        vals=np.array([float(x['equity']) for x in curve[-80:]],float)
        recent_eq=vals[-20:];peak=np.maximum.accumulate(vals)
        dd=(vals/np.maximum(peak,1e-9)-1)*100
        if float(dd[-20:].min())<=-5:flags.append('RECENT_DRAWDOWN');score+=15
        if len(recent_eq)>=10:
            slope=np.polyfit(np.arange(len(recent_eq)),recent_eq,1)[0]
            if slope<0:flags.append('NEGATIVE_EQUITY_SLOPE');score+=10
    status='DECAY' if score>=45 else 'WATCH' if score>=25 else 'STABLE'
    return {'status':status,'score':min(100,score),'closed_trades':len(pnls),'window':w,'flags':flags,
            'prior':{k:(round(v,3) if isinstance(v,float) and math.isfinite(v) else v) for k,v in prior.items()},
            'recent':{k:(round(v,3) if isinstance(v,float) and math.isfinite(v) else v) for k,v in recent.items()},
            'note':'Forward paper degradation diagnostic. DECAY blocks promotion but does not automatically liquidate positions.'}
