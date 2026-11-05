"""V98 adversarial market stress 3.0.
Extends deterministic OHLCV hostile-pattern testing and requires joint Signal Guard / Trap Defense awareness.
Never attributes manipulation intent or actor identity.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .adversarial_v2 import stress as stress_v2,_frame,_atr,_set
from .trap_defense import assess_traps
from .signal_guard import assess as assess_signal_guard

EXTRA_SCENARIOS={
 'close_spike_reversal':'Late-session style close spike proxy followed by immediate reversal.',
 'volume_inflation_no_progress':'Extreme volume with repeated small bodies and little net price progress.',
 'breakout_retest_failure':'Breakout, weak retest hold and then decisive failure below the reference.',
 'gap_chase_fade_cluster':'Repeated gap-up opens that fade before the close.',
 'liquidity_vacuum_squeeze':'Price stretches higher while volume collapses, then reverses on restored volume.',
}

def inject_extra(df,scenario):
    if scenario not in EXTRA_SCENARIOS:raise ValueError('Unknown V98 scenario.')
    x=_frame(df);a=_atr(x);vbase=float(x.Volume.iloc[-40:-10].median())
    resistance=float(x.High.iloc[-40:-10].max());start=-8;prev=float(x.Close.iloc[start-1])
    if scenario=='close_spike_reversal':
        for k in range(5):
            close=prev+.15*a;_set(x,start+k,prev,close+.25*a,prev-.2*a,close,vbase);prev=close
        close=prev+2.2*a;_set(x,-3,prev,close+.15*a,prev-.15*a,close,vbase*2.8);prev=close
        close=prev-1.7*a;_set(x,-2,prev,prev+.2*a,close-.4*a,close,vbase*3.2);prev=close
        close=prev-1.2*a;_set(x,-1,prev,prev+.15*a,close-.35*a,close,vbase*2.6)
    elif scenario=='volume_inflation_no_progress':
        for k in range(8):
            o=prev;close=prev+(.05*a if k%2==0 else -.04*a)
            _set(x,start+k,o,max(o,close)+.35*a,min(o,close)-.35*a,close,vbase*(2.5+.45*k));prev=close
    elif scenario=='breakout_retest_failure':
        close=resistance+1.0*a;_set(x,start,prev,close+.3*a,prev-.2*a,close,vbase*2.0);prev=close
        for k in range(1,4):
            close=resistance+(.45-.1*k)*a;_set(x,start+k,prev,prev+.25*a,resistance-.05*a,close,vbase*1.35);prev=close
        for k in range(4,8):
            close=prev-(.55+.15*(k-4))*a;_set(x,start+k,prev,prev+.2*a,close-.45*a,close,vbase*(1.8+.35*(k-4)));prev=close
    elif scenario=='gap_chase_fade_cluster':
        for k in range(8):
            o=prev+1.0*a;close=o-(.55+.05*k)*a;_set(x,start+k,o,o+.4*a,close-.35*a,close,vbase*(1.6+.2*k));prev=close
    elif scenario=='liquidity_vacuum_squeeze':
        for k in range(5):
            close=prev+(.55+.15*k)*a;_set(x,start+k,prev,close+.5*a,prev-.25*a,close,vbase*(.35-.04*k));prev=close
        for k in range(5,8):
            close=prev-(1.0+.15*(k-5))*a;_set(x,start+k,prev,prev+.25*a,close-.55*a,close,vbase*(2.8+.5*(k-5)));prev=close
    return x

def _judge(df):
    trap=assess_traps(df);guard=assess_signal_guard(df)
    detected_trap=trap.get('status') in {'WAIT','BLOCK'}
    detected_guard=guard.get('status') in {'WAIT','BLOCK'}
    return {'trap_status':trap.get('status'),'trap_score':trap.get('score'),
            'guard_status':guard.get('status'),'guard_score':guard.get('score'),
            'trap_flags':[x.get('code') for x in (trap.get('flags') or [])],
            'guard_flags':[x.get('code') for x in (guard.get('flags') or [])],
            'detected_any':detected_trap or detected_guard,'detected_both':detected_trap and detected_guard}

def stress(df):
    base=_frame(df);legacy=stress_v2(base);extra=[]
    for name,desc in EXTRA_SCENARIOS.items():
        r=_judge(inject_extra(base,name));extra.append({'scenario':name,'description':desc,**r})
    legacy_rows=[]
    from .adversarial_v2 import MULTI_SCENARIOS,inject_multiday
    for name,desc in MULTI_SCENARIOS.items():
        r=_judge(inject_multiday(base,name));legacy_rows.append({'scenario':name,'description':desc,**r})
    rows=legacy_rows+extra
    any_rate=sum(1 for x in rows if x['detected_any'])/max(1,len(rows))*100
    both_rate=sum(1 for x in rows if x['detected_both'])/max(1,len(rows))*100
    misses=[x['scenario'] for x in rows if not x['detected_any']]
    return {'status':'PASS' if not misses else 'WEAK','version':3,'scenarios':rows,'scenario_count':len(rows),
            'detected_any_pct':round(any_rate,1),'detected_both_pct':round(both_rate,1),'missed_scenarios':misses,
            'v2_baseline_rate_pct':legacy.get('detection_rate_pct'),
            'limits':'Deterministic synthetic OHLCV robustness test only. It cannot prove manipulation, spoofing, wash trading, closing-price intent or identify an actor; Level-2/order-event/trade-side data is required for those claims.'}
