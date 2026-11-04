"""V75 adversarial market stress 2.0.
Deterministic multi-bar and cross-sectional hostile-pattern tests.
These scenarios test robustness to deceptive-looking OHLCV structures; they do not infer manipulation intent.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .trap_defense import assess_traps

MULTI_SCENARIOS={
 'false_breakout_distribution':'Three breakout attempts with fading closes and rising volume, followed by distribution.',
 'repeated_stop_sweeps':'Repeated low sweeps/reclaims that attempt to trigger weak stops before a final downside rejection.',
 'liquidity_vacuum_reversal':'Range expands while volume collapses, followed by a high-volume reversal.',
 'staircase_pump_fade':'Several accelerating up bars with rising volume followed by a two-bar high-volume fade.'
}

def _frame(df,min_bars=120):
    need=['Open','High','Low','Close','Volume']
    if df is None or len(df)<min_bars or any(k not in df for k in need):
        raise ValueError(f'V75 adversarial stress requires at least {min_bars} OHLCV bars.')
    x=df[need].apply(pd.to_numeric,errors='coerce').astype(float).copy()
    if not np.isfinite(x.to_numpy()).all():raise ValueError('OHLCV must be finite.')
    return x

def _atr(x):
    c=x.Close
    tr=pd.concat([(x.High-x.Low).abs(),(x.High-c.shift()).abs(),(x.Low-c.shift()).abs()],axis=1).max(axis=1)
    v=float(tr.rolling(14).mean().iloc[-10])
    return max(v,float(c.iloc[-10])*.008)

def _set(x,pos,o,h,l,c,v):
    h=max(h,o,c,l);l=min(l,o,c,h)
    x.iloc[pos,x.columns.get_loc('Open')]=o
    x.iloc[pos,x.columns.get_loc('High')]=h
    x.iloc[pos,x.columns.get_loc('Low')]=l
    x.iloc[pos,x.columns.get_loc('Close')]=c
    x.iloc[pos,x.columns.get_loc('Volume')]=max(0,v)

def inject_multiday(df,scenario):
    if scenario not in MULTI_SCENARIOS:raise ValueError('Unknown V75 scenario.')
    x=_frame(df);a=_atr(x);vbase=float(x.Volume.iloc[-40:-10].median())
    resistance=float(x.High.iloc[-40:-10].max());support=float(x.Low.iloc[-40:-10].min())
    start=-8
    if scenario=='false_breakout_distribution':
        prev=float(x.Close.iloc[start-1])
        for k in range(4):
            o=prev+.1*a;c=resistance-(.05+.12*k)*a;h=resistance+(1.0+.25*k)*a;l=min(o,c)-.35*a
            _set(x,start+k,o,h,l,c,vbase*(1.8+.6*k));prev=c
        for k in range(4,8):
            o=prev;c=prev-(.35+.08*(k-4))*a;h=o+.4*a;l=c-.6*a
            _set(x,start+k,o,h,l,c,vbase*(2.6+.25*(k-4)));prev=c
    elif scenario=='repeated_stop_sweeps':
        prev=float(x.Close.iloc[start-1])
        for k in range(6):
            low=support-(.35+.18*k)*a
            close=support+(.35 if k<4 else -.25*(k-3))*a
            _set(x,start+k,prev,prev+.45*a,low,close,vbase*(1.5+.25*k));prev=close
        for k in range(6,8):
            close=prev-.8*a;_set(x,start+k,prev,prev+.2*a,close-.45*a,close,vbase*3.0);prev=close
    elif scenario=='liquidity_vacuum_reversal':
        prev=float(x.Close.iloc[start-1])
        for k in range(5):
            direction=1 if k<3 else -1
            close=prev+direction*(.7+.2*k)*a
            _set(x,start+k,prev,max(prev,close)+1.1*a,min(prev,close)-1.1*a,close,vbase*(.22-.025*k));prev=close
        for k in range(5,8):
            close=prev-1.05*a
            _set(x,start+k,prev,prev+.35*a,close-.7*a,close,vbase*(3.0+.5*(k-5)));prev=close
    elif scenario=='staircase_pump_fade':
        prev=float(x.Close.iloc[start-1])
        for k in range(6):
            close=prev*(1.012+.004*k)
            _set(x,start+k,prev,close+(.25+.1*k)*a,prev-.2*a,close,vbase*(1.25+.45*k));prev=close
        for k in range(6,8):
            close=prev*(.94 if k==6 else .92)
            _set(x,start+k,prev,prev+.3*a,close-.5*a,close,vbase*(4.0+.8*(k-6)));prev=close
    return x

def stress(df):
    base=_frame(df);baseline=assess_traps(base);rows=[]
    for name,desc in MULTI_SCENARIOS.items():
        altered=inject_multiday(base,name);r=assess_traps(altered)
        rows.append({'scenario':name,'description':desc,'status':r.get('status'),'score':r.get('score'),
                     'flags':[f.get('code') for f in (r.get('flags') or [])],
                     'detected':r.get('status') in {'WAIT','BLOCK'}})
    detected=sum(1 for x in rows if x['detected'])
    return {'version':2,'baseline':{'status':baseline.get('status'),'score':baseline.get('score')},
            'scenarios':rows,'detected_count':detected,'total':len(rows),
            'detection_rate_pct':round(detected/max(1,len(rows))*100,1),
            'pass':detected==len(rows),
            'limits':'Deterministic synthetic OHLCV stress only. It tests response to hostile-looking multi-bar patterns; it cannot prove manipulation or infer actor intent.'}

def cross_sectional_stress(frames,min_names=5):
    usable={}
    for code,df in (frames or {}).items():
        try:usable[str(code)]=_frame(df)
        except Exception:continue
    if len(usable)<min_names:return {'status':'INSUFFICIENT_NAMES','names':len(usable)}
    rows=[]
    for i,(code,df) in enumerate(sorted(usable.items())):
        scenario='staircase_pump_fade' if i%2==0 else 'false_breakout_distribution'
        r=assess_traps(inject_multiday(df,scenario))
        rows.append({'ticker':code,'scenario':scenario,'status':r.get('status'),'score':r.get('score'),
                     'detected':r.get('status') in {'WAIT','BLOCK'}})
    rate=sum(1 for x in rows if x['detected'])/len(rows)*100
    return {'status':'OK','names':len(rows),'detected_pct':round(rate,1),'rows':rows,
            'cluster_status':'PASS' if rate>=80 else 'WEAK',
            'note':'Cross-sectional synchronized synthetic stress. It tests whether simultaneous hostile patterns are caught without attributing intent.'}
