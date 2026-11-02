"""V41 Trade Reality Engine.
Conservative intraday replay before paper sizing. Uses completed 15-minute BIST bars
from prior sessions only, regime/volatility-aware block bootstrap and stop-first
intrabar resolution. It is a distributional stress check, never a prediction.
"""
from __future__ import annotations
import math
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo
from .market_data import yahoo_rows

TR=ZoneInfo('Europe/Istanbul')

def _session_rows(ticker):
    rows=yahoo_rows(ticker,period='1mo',interval='15m').get('candles',[])
    days={}
    for r in rows:
        try:
            dt=datetime.fromtimestamp(int(r['time']),TR)
            # BIST regular continuous session; keep ordinary daytime bars only.
            if dt.weekday()>=5 or not (10<=dt.hour<18):continue
            days.setdefault(dt.date().isoformat(),[]).append({**r,'slot':dt.hour*4+dt.minute//15})
        except Exception:continue
    for d in days:days[d].sort(key=lambda x:x['time'])
    return days

def _bar_ratio(prev_close,b):
    if prev_close<=0:return None
    return np.array([b['open']/prev_close,b['high']/prev_close,b['low']/prev_close,b['close']/prev_close],float)

def _volatility(day):
    c=np.array([x['close'] for x in day],float)
    if len(c)<4:return None
    r=np.diff(np.log(c))
    return float(np.std(r))

def _regime(day):
    if len(day)<4:return 'MIXED'
    ret=day[-1]['close']/day[0]['open']-1
    return 'UP' if ret>.005 else 'DOWN' if ret<-.005 else 'FLAT'

def trade_reality(ticker,entry,stop,target,side='BUY',simulations=10000,seed=41,block_bars=3):
    side=str(side).upper()
    if side not in {'BUY','SHORT'}:raise ValueError('side must be BUY or SHORT')
    entry=float(entry);stop=float(stop);target=float(target)
    long=side=='BUY'
    risk=(entry-stop) if long else (stop-entry)
    reward=(target-entry) if long else (entry-target)
    if min(entry,stop,target)<=0 or risk<=0 or reward<=0:raise ValueError('invalid entry/stop/target geometry')
    days=_session_rows(ticker)
    today=datetime.now(TR).date().isoformat()
    sessions=[v for d,v in sorted(days.items()) if d<today and len(v)>=16]
    if len(sessions)<10:return {'ticker':ticker.upper(),'status':'INSUFFICIENT_DATA','sessions':len(sessions),'required_sessions':10}
    vols=np.array([_volatility(x) or 0 for x in sessions]);med=float(np.median(vols))
    regimes=[_regime(x) for x in sessions]
    # Today/context proxy: use most recent completed prior session. Prefer similar regime/volatility,
    # but fall back to all sessions to avoid tiny-sample false precision.
    anchor=sessions[-1];av=_volatility(anchor) or med;ar=_regime(anchor)
    idx=[i for i,(v,r) in enumerate(zip(vols,regimes)) if r==ar and (med==0 or .55<=v/max(av,1e-9)<=1.8)]
    if len(idx)<6:idx=list(range(len(sessions)))
    pool=[sessions[i] for i in idx]
    # Convert each source session to causal blocks of OHLC ratios.
    blocks=[]
    B=max(1,min(int(block_bars),6))
    for day in pool:
        ratios=[]
        prev=day[0]['open']
        for b in day:
            x=_bar_ratio(prev,b)
            if x is not None:ratios.append(x)
            prev=b['close']
        for j in range(0,max(0,len(ratios)-B+1)):
            blocks.append(ratios[j:j+B])
    if not blocks:return {'ticker':ticker.upper(),'status':'INSUFFICIENT_DATA','sessions':len(sessions)}
    rng=np.random.default_rng(seed);n=max(1000,min(int(simulations),50000))
    target_n=stop_n=close_n=0;final_r=[];paths_dd=[]
    target_r=reward/risk
    horizon=min(24,max(8,int(np.median([len(x) for x in sessions]))))
    for _ in range(n):
        p=entry;out=None;peak=p;maxdd=0;used=0
        while used<horizon and out is None:
            block=blocks[int(rng.integers(0,len(blocks)))]
            for ratio in block:
                o,h,l,c=p*ratio[0],p*ratio[1],p*ratio[2],p*ratio[3]
                if long:
                    if l<=stop:out='STOP';p=min(o,stop);break
                    if h>=target:out='TARGET';p=target;break
                else:
                    if h>=stop:out='STOP';p=max(o,stop);break
                    if l<=target:out='TARGET';p=target;break
                p=c;used+=1
                peak=max(peak,p) if long else min(peak,p)
                dd=(p/peak-1) if long else (peak/p-1)
                maxdd=min(maxdd,dd)
                if used>=horizon:break
        if out=='TARGET':target_n+=1;r=target_r
        elif out=='STOP':stop_n+=1;r=-1.0
        else:
            close_n+=1;r=((p-entry) if long else (entry-p))/risk
        final_r.append(r);paths_dd.append(maxdd*100)
    arr=np.array(final_r,float);hit=target_n+stop_n
    target_given_hit=target_n/hit if hit else 0
    breakeven=1/(1+target_r)
    edge=target_given_hit-breakeven
    verdict='FAVORABLE' if edge>=.10 and np.mean(arr)>0 else 'MARGINAL' if edge>=-.03 and np.mean(arr)>=-.1 else 'UNFAVORABLE'
    return {
      'ticker':ticker.upper(),'status':'OK','side':side,'entry':entry,'stop':stop,'target':target,
      'sessions':len(sessions),'conditioned_sessions':len(pool),'simulations':n,'seed':seed,'block_bars':B,
      'target_first_pct':round(target_n/n*100,1),'stop_first_pct':round(stop_n/n*100,1),
      'neither_pct':round(close_n/n*100,1),'target_given_hit_pct':round(target_given_hit*100,1),
      'breakeven_hit_pct':round(breakeven*100,1),'avg_r':round(float(np.mean(arr)),3),
      'median_r':round(float(np.median(arr)),3),'r_p10':round(float(np.quantile(arr,.10)),3),
      'r_p90':round(float(np.quantile(arr,.90)),3),'loss_probability_pct':round(float(np.mean(arr<0)*100),1),
      'maxdd_p10_pct':round(float(np.quantile(paths_dd,.10)),2),'verdict':verdict,
      'method':'Prior-session 15m regime/volatility-conditioned block bootstrap; stop-first within ambiguous bars.',
      'limits':'Distributional stress check only. Yahoo intraday data can lag; halts, gaps, price limits and Level-2 effects can exceed the sampled history.'
    }
