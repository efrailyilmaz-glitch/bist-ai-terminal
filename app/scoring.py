from __future__ import annotations
import math
import numpy as np
import pandas as pd

def _num(x, default=0.0):
    try:
        v=float(x); return default if math.isnan(v) or math.isinf(v) else v
    except Exception: return default

def rsi(close: pd.Series, n=14):
    d=close.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    rs=up.ewm(alpha=1/n,adjust=False).mean()/dn.ewm(alpha=1/n,adjust=False).mean().replace(0,np.nan)
    return 100-(100/(1+rs))

def atr(df: pd.DataFrame,n=14):
    pc=df['Close'].shift(1); tr=pd.concat([(df['High']-df['Low']).abs(),(df['High']-pc).abs(),(df['Low']-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False).mean()

def score_frame(df: pd.DataFrame):
    df=df.dropna(subset=['Close']).copy()
    if len(df)<22: return None
    c=df['Close'].astype(float); v=df.get('Volume',pd.Series(index=df.index,dtype=float)).fillna(0).astype(float)
    last=_num(c.iloc[-1]); prev=_num(c.iloc[-2],last)
    ma20=c.rolling(20).mean(); ma50=c.rolling(50).mean(); ma200=c.rolling(200).mean()
    rv=rsi(c); av=atr(df); vol20=v.rolling(20).mean()
    mom5=(last/_num(c.iloc[-6],last)-1)*100 if len(c)>=6 else 0
    mom20=(last/_num(c.iloc[-21],last)-1)*100 if len(c)>=21 else 0
    mom60=(last/_num(c.iloc[-61],last)-1)*100 if len(c)>=61 else mom20
    mom120=(last/_num(c.iloc[-121],last)-1)*100 if len(c)>=121 else mom60
    r=_num(rv.iloc[-1],50); vr=_num(v.iloc[-1]/vol20.iloc[-1],1) if len(vol20) else 1
    hi20=_num(c.shift(1).rolling(20).max().iloc[-1],last); breakout=last>hi20 if hi20 else False
    volat=_num(c.pct_change().tail(20).std()*np.sqrt(252)*100,0)
    s=50
    s += 12 if last>_num(ma20.iloc[-1],last) else -10
    s += 10 if _num(ma20.iloc[-1])>_num(ma50.iloc[-1]) else -8
    s += max(-10,min(12,mom20*.7)); s += max(-5,min(8,(vr-1)*8))
    s += 8 if breakout else 0; s += 5 if 48<=r<=68 else (-8 if r>80 else -3 if r<30 else 0)
    short=int(max(0,min(100,round(s))))
    l=50
    if len(c)>=200: l += 15 if last>_num(ma200.iloc[-1]) else -15
    l += 12 if _num(ma50.iloc[-1])>_num(ma200.iloc[-1],_num(ma50.iloc[-1])) else -8
    l += max(-12,min(15,mom120*.35)); l += max(-8,min(10,mom60*.25)); l -= max(0,min(12,(volat-35)*.25))
    long=int(max(0,min(100,round(l))))
    a=_num(av.iloc[-1],last*.03); risk=int(max(0,min(100,round(volat*1.4))))
    gap=abs((last/prev-1)*100) if prev else 0
    anomaly=int(max(0,min(100,round(max(0,vr-1)*24 + max(0,gap-3)*6 + max(0,volat-45)*0.7))))
    smart=int(max(0,min(100,round(50 + (12 if last>_num(ma20.iloc[-1]) else -10) + max(-12,min(18,(vr-1)*12)) + max(-10,min(15,mom20*.4))))))
    alpha=int(max(0,min(100,round(short*.55 + long*.45 - risk*.12))))
    reasons_short=[]
    if breakout: reasons_short.append('20G breakout')
    if mom20>5: reasons_short.append(f'20G momentum +%{mom20:.1f}')
    if vr>1.5: reasons_short.append(f'hacim {vr:.1f}x')
    if last>_num(ma20.iloc[-1]): reasons_short.append('MA20 üstü')
    reasons_long=[]
    if len(c)>=200 and last>_num(ma200.iloc[-1]): reasons_long.append('MA200 üstü')
    if _num(ma50.iloc[-1])>_num(ma200.iloc[-1],_num(ma50.iloc[-1])): reasons_long.append('uzun trend pozitif')
    if mom120>10: reasons_long.append(f'6A momentum +%{mom120:.1f}')
    return {
      'price':round(last,2),'change':round((last/prev-1)*100,2) if prev else 0,'short_score':short,'long_score':long,
      'short_signal':'GÜÇLÜ' if short>=80 else 'POZİTİF' if short>=68 else 'NÖTR' if short>=48 else 'ZAYIF',
      'long_signal':'GÜÇLÜ' if long>=80 else 'POZİTİF' if long>=68 else 'NÖTR' if long>=48 else 'ZAYIF',
      'rsi':round(r,1),'volume_ratio':round(vr,2),'momentum_5':round(mom5,2),'momentum_20':round(mom20,2),'momentum_60':round(mom60,2),'momentum_120':round(mom120,2),
      'volatility':round(volat,1),'risk':risk,'anomaly_score':anomaly,'smart_money_score':smart,'alpha_score':alpha,'breakout20':bool(breakout),'trend':'YUKARI' if last>_num(ma20.iloc[-1])>_num(ma50.iloc[-1]) else 'AŞAĞI' if last<_num(ma20.iloc[-1])<_num(ma50.iloc[-1]) else 'YATAY',
      'target_short':round(last+2*a,2),'stop_short':round(max(0,last-1.4*a),2),'reasons_short':reasons_short[:3],'reasons_long':reasons_long[:3],
      'spark':[round(_num(x),2) for x in c.tail(30).tolist()]}
