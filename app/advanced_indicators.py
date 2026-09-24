from __future__ import annotations
import math
from typing import Dict, List
import numpy as np
import pandas as pd

def _num(x, default=0.0):
    try:
        v=float(x)
        return default if math.isnan(v) or math.isinf(v) else v
    except Exception:
        return default

def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d=close.diff()
    up=d.clip(lower=0)
    dn=-d.clip(upper=0)
    rs=up.ewm(alpha=1/n,adjust=False,min_periods=n).mean()/dn.ewm(alpha=1/n,adjust=False,min_periods=n).mean().replace(0,np.nan)
    return 100-(100/(1+rs))

def _atr(df: pd.DataFrame, n: int = 10) -> pd.Series:
    pc=df['Close'].shift(1)
    tr=pd.concat([
        (df['High']-df['Low']).abs(),
        (df['High']-pc).abs(),
        (df['Low']-pc).abs()
    ],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()

def add_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    out=df.copy()
    hl2=(out['High']+out['Low'])/2
    a=_atr(out,period)
    upper=hl2+multiplier*a
    lower=hl2-multiplier*a
    final_upper=upper.copy()
    final_lower=lower.copy()
    trend=pd.Series(True,index=out.index,dtype=bool)
    st=pd.Series(np.nan,index=out.index,dtype=float)

    for i in range(1,len(out)):
        prev=i-1
        if pd.isna(a.iloc[i]):
            continue
        final_upper.iloc[i]=upper.iloc[i] if (upper.iloc[i]<final_upper.iloc[prev] or out['Close'].iloc[prev]>final_upper.iloc[prev]) else final_upper.iloc[prev]
        final_lower.iloc[i]=lower.iloc[i] if (lower.iloc[i]>final_lower.iloc[prev] or out['Close'].iloc[prev]<final_lower.iloc[prev]) else final_lower.iloc[prev]

        if trend.iloc[prev]:
            trend.iloc[i]=False if out['Close'].iloc[i]<final_lower.iloc[i] else True
        else:
            trend.iloc[i]=True if out['Close'].iloc[i]>final_upper.iloc[i] else False
        st.iloc[i]=final_lower.iloc[i] if trend.iloc[i] else final_upper.iloc[i]

    out['SUPERTREND']=st
    out['SUPERTREND_BULL']=trend
    return out

def add_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    out=df.copy()
    high=out['High'].astype(float)
    low=out['Low'].astype(float)
    tenkan=(high.rolling(9).max()+low.rolling(9).min())/2
    kijun=(high.rolling(26).max()+low.rolling(26).min())/2
    span_a=((tenkan+kijun)/2).shift(26)
    span_b=((high.rolling(52).max()+low.rolling(52).min())/2).shift(26)
    chikou=out['Close'].shift(-26)
    out['TENKAN']=tenkan
    out['KIJUN']=kijun
    out['ICHIMOKU_A']=span_a
    out['ICHIMOKU_B']=span_b
    out['CHIKOU']=chikou
    return out

def _pivots(series: pd.Series, window: int = 3, low: bool = True) -> List[int]:
    vals=series.astype(float).values
    idx=[]
    for i in range(window,len(vals)-window):
        seg=vals[i-window:i+window+1]
        if not np.isfinite(vals[i]):
            continue
        if low and vals[i]==np.nanmin(seg):
            idx.append(i)
        elif not low and vals[i]==np.nanmax(seg):
            idx.append(i)
    return idx

def detect_divergence(df: pd.DataFrame, lookback: int = 80) -> Dict:
    close=df['Close'].astype(float)
    r=_rsi(close)
    ema12=close.ewm(span=12,adjust=False,min_periods=12).mean()
    ema26=close.ewm(span=26,adjust=False,min_periods=26).mean()
    macd_hist=(ema12-ema26)-(ema12-ema26).ewm(span=9,adjust=False,min_periods=9).mean()
    start=max(0,len(df)-lookback)
    c=close.iloc[start:].reset_index(drop=True)
    rr=r.iloc[start:].reset_index(drop=True)
    mh=macd_hist.iloc[start:].reset_index(drop=True)
    lows=_pivots(c,3,True)
    highs=_pivots(c,3,False)

    result={'rsi':'NONE','macd':'NONE','rsi_strength':0,'macd_strength':0}
    if len(lows)>=2:
        a,b=lows[-2],lows[-1]
        if c.iloc[b]<c.iloc[a] and rr.iloc[b]>rr.iloc[a]:
            result['rsi']='BULLISH'
            result['rsi_strength']=round(float((rr.iloc[b]-rr.iloc[a])+abs((c.iloc[b]/c.iloc[a]-1)*100)),1)
        if c.iloc[b]<c.iloc[a] and mh.iloc[b]>mh.iloc[a]:
            result['macd']='BULLISH'
            result['macd_strength']=round(float((mh.iloc[b]-mh.iloc[a])/(abs(mh.iloc[a])+1e-9)),2)
    if len(highs)>=2:
        a,b=highs[-2],highs[-1]
        if c.iloc[b]>c.iloc[a] and rr.iloc[b]<rr.iloc[a]:
            result['rsi']='BEARISH'
            result['rsi_strength']=round(float((rr.iloc[a]-rr.iloc[b])+abs((c.iloc[b]/c.iloc[a]-1)*100)),1)
        if c.iloc[b]>c.iloc[a] and mh.iloc[b]<mh.iloc[a]:
            result['macd']='BEARISH'
            result['macd_strength']=round(float((mh.iloc[a]-mh.iloc[b])/(abs(mh.iloc[a])+1e-9)),2)
    return result

def cross_state(df: pd.DataFrame, fast: int = 50, slow: int = 200, recent: int = 12) -> Dict:
    close=df['Close'].astype(float)
    ef=close.ewm(span=fast,adjust=False,min_periods=min(fast,len(close))).mean()
    es=close.ewm(span=slow,adjust=False,min_periods=min(slow,len(close))).mean()
    diff=ef-es
    state='GOLDEN' if _num(diff.iloc[-1])>0 else 'DEATH'
    event='NONE'
    window=diff.tail(recent+1)
    signs=np.sign(window.fillna(0).values)
    for i in range(1,len(signs)):
        if signs[i]>0 and signs[i-1]<=0:
            event='GOLDEN_CROSS'
        elif signs[i]<0 and signs[i-1]>=0:
            event='DEATH_CROSS'
    return {'state':state,'recent_event':event,'spread_pct':round(_num(diff.iloc[-1])/_num(close.iloc[-1],1)*100,2)}

def bollinger_squeeze(df: pd.DataFrame) -> Dict:
    c=df['Close'].astype(float)
    mid=c.rolling(20).mean()
    width=((mid+2*c.rolling(20).std())-(mid-2*c.rolling(20).std()))/mid.replace(0,np.nan)*100
    last=_num(width.iloc[-1])
    hist=width.tail(120).dropna()
    pct=float((hist<=last).mean()*100) if len(hist) else 50
    squeeze=pct<=20
    return {'active':bool(squeeze),'width':round(last,2),'percentile':round(pct,1)}

def support_resistance(df: pd.DataFrame, lookback: int = 160, max_levels: int = 3) -> Dict:
    sub=df.tail(lookback).copy()
    if len(sub)<15:
        return {'supports':[],'resistances':[]}
    close=_num(sub['Close'].iloc[-1])
    atrv=_num(_atr(sub,14).iloc[-1],max(close*.02,0.01))
    tolerance=max(atrv*.55,close*.005)
    levels=[]
    for col,is_low in [('Low',True),('High',False)]:
        s=sub[col].astype(float).reset_index(drop=True)
        for i in _pivots(s,3,is_low):
            levels.append(float(s.iloc[i]))
    levels.sort()
    clusters=[]
    for x in levels:
        if not clusters or abs(x-np.mean(clusters[-1]))>tolerance:
            clusters.append([x])
        else:
            clusters[-1].append(x)
    merged=[round(float(np.mean(c)),4) for c in clusters if len(c)>=2]
    supports=sorted([x for x in merged if x<close],reverse=True)[:max_levels]
    resistances=sorted([x for x in merged if x>close])[:max_levels]
    return {'supports':supports,'resistances':resistances}

def analyze_structure(df: pd.DataFrame) -> Dict:
    if df is None or len(df)<30:
        return {
            'supertrend':'UNKNOWN','ichimoku':'UNKNOWN','cross':{'state':'UNKNOWN','recent_event':'NONE','spread_pct':0},
            'squeeze':{'active':False,'width':0,'percentile':50},'divergence':{'rsi':'NONE','macd':'NONE'},
            'supports':[],'resistances':[]
        }
    x=add_ichimoku(add_supertrend(df))
    last=x.iloc[-1]
    close=_num(last['Close'])
    st_bull=bool(last.get('SUPERTREND_BULL',False))
    a=_num(last.get('ICHIMOKU_A'),np.nan)
    b=_num(last.get('ICHIMOKU_B'),np.nan)
    tenkan=_num(last.get('TENKAN'),np.nan)
    kijun=_num(last.get('KIJUN'),np.nan)
    if np.isfinite(a) and np.isfinite(b):
        top=max(a,b); bot=min(a,b)
        ichi='BULLISH' if close>top and tenkan>=kijun else ('BEARISH' if close<bot and tenkan<kijun else 'NEUTRAL')
    else:
        ichi='UNKNOWN'
    sr=support_resistance(x)
    return {
        'supertrend':'BULLISH' if st_bull else 'BEARISH',
        'supertrend_value':round(_num(last.get('SUPERTREND')),4),
        'ichimoku':ichi,
        'tenkan':round(tenkan,4) if np.isfinite(tenkan) else None,
        'kijun':round(kijun,4) if np.isfinite(kijun) else None,
        'ichimoku_a':round(a,4) if np.isfinite(a) else None,
        'ichimoku_b':round(b,4) if np.isfinite(b) else None,
        'cross':cross_state(x),
        'squeeze':bollinger_squeeze(x),
        'divergence':detect_divergence(x),
        'supports':sr['supports'],
        'resistances':sr['resistances']
    }

def advanced_series(df: pd.DataFrame) -> Dict:
    x=add_ichimoku(add_supertrend(df))
    return {
        'supertrend':x['SUPERTREND'],
        'supertrend_bull':x['SUPERTREND_BULL'],
        'tenkan':x['TENKAN'],
        'kijun':x['KIJUN'],
        'ichimoku_a':x['ICHIMOKU_A'],
        'ichimoku_b':x['ICHIMOKU_B']
    }
