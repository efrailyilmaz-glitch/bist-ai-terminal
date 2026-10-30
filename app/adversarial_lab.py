"""Adversarial OHLCV stress lab for Trap Defense.
Synthetic patterns are deterministic safety tests, never claims of real manipulation.
"""
from __future__ import annotations
import copy
import numpy as np
import pandas as pd
from .trap_defense import assess_traps

SCENARIOS={
    'fake_breakout':'Prior resistance is pierced but the bar closes back below it on heavy volume.',
    'gap_trap':'Large gap-up opens above prior close and fades to a weak close.',
    'stop_sweep':'Price sweeps below the prior 20-bar low and reclaims it before close.',
    'volume_climax':'Range and volume expand sharply while the close finishes weak.',
    'pump_fade':'A fast multi-bar run is followed by a high-volume three-bar reversal.'
}

def _frame(df):
    need=['Open','High','Low','Close','Volume']
    if df is None or len(df)<80 or any(k not in df for k in need):
        raise ValueError('Adversarial lab requires at least 80 OHLCV bars.')
    x=df[need].apply(pd.to_numeric,errors='coerce').copy()
    if not np.isfinite(x.to_numpy()).all():
        raise ValueError('OHLCV must be finite.')
    return x

def _atr(x,n=14):
    c=x.Close
    tr=pd.concat([(x.High-x.Low).abs(),(x.High-c.shift()).abs(),(x.Low-c.shift()).abs()],axis=1).max(axis=1)
    return float(tr.rolling(n).mean().iloc[-2])

def inject(df,scenario):
    if scenario not in SCENARIOS: raise ValueError('Unknown adversarial scenario.')
    x=_frame(df)
    a=max(_atr(x),float(x.Close.iloc[-2])*.01)
    prev=float(x.Close.iloc[-2]);vbase=float(x.Volume.iloc[-22:-2].median())
    high20=float(x.High.iloc[-22:-2].max());low20=float(x.Low.iloc[-22:-2].min())
    i=x.index[-1]
    if scenario=='fake_breakout':
        x.loc[i]=[high20+.15*a,high20+1.2*a,high20-.6*a,high20-.2*a,max(vbase*3,float(x.Volume.iloc[-1]))]
    elif scenario=='gap_trap':
        op=prev+1.8*a;x.loc[i]=[op,op+.35*a,prev-.25*a,prev+.05*a,max(vbase*3.2,float(x.Volume.iloc[-1]))]
    elif scenario=='stop_sweep':
        x.loc[i]=[prev,prev+.45*a,low20-.9*a,low20+.35*a,max(vbase*2,float(x.Volume.iloc[-1]))]
    elif scenario=='volume_climax':
        op=prev+.4*a;x.loc[i]=[op,op+1.6*a,prev-1.4*a,prev-.8*a,max(vbase*4.5,float(x.Volume.iloc[-1]))]
    elif scenario=='pump_fade':
        for j,m in zip([-4,-3,-2],[1.08,1.16,1.22]):
            base=float(x.Close.iloc[j-1]);close=base*m
            x.iloc[j,x.columns.get_loc('Open')]=base*1.01
            x.iloc[j,x.columns.get_loc('High')]=close*1.01
            x.iloc[j,x.columns.get_loc('Low')]=base*.99
            x.iloc[j,x.columns.get_loc('Close')]=close
            x.iloc[j,x.columns.get_loc('Volume')]=vbase*2
        peak=float(x.Close.iloc[-2]);x.loc[i]=[peak*.99,peak*1.01,peak*.88,peak*.90,vbase*3.5]
    return x

def stress(df):
    base=_frame(df)
    baseline=assess_traps(base)
    rows=[]
    for name in SCENARIOS:
        altered=inject(base,name)
        result=assess_traps(altered)
        rows.append({'scenario':name,'description':SCENARIOS[name],'status':result['status'],'score':result['score'],
                     'flags':[f['code'] for f in result.get('flags',[])],
                     'detected':result['status'] in {'WAIT','BLOCK'}})
    detected=sum(1 for r in rows if r['detected'])
    return {'version':1,'baseline':{'status':baseline['status'],'score':baseline['score']},
            'scenarios':rows,'detected_count':detected,'total':len(rows),
            'detection_rate_pct':round(detected/len(rows)*100,1),
            'pass':detected==len(rows),
            'limits':'Synthetic OHLCV stress only. It tests whether heuristics react to hostile-looking price/volume patterns; it cannot prove manipulation or model Level-2 order behavior.'}
