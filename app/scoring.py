from __future__ import annotations
import math
import numpy as np
import pandas as pd

def _num(x, default=0.0):
    try:
        v=float(x)
        return default if math.isnan(v) or math.isinf(v) else v
    except Exception:
        return default

def rsi(close: pd.Series, n=14):
    d=close.diff()
    up=d.clip(lower=0)
    dn=-d.clip(upper=0)
    rs=up.ewm(alpha=1/n,adjust=False,min_periods=n).mean()/dn.ewm(alpha=1/n,adjust=False,min_periods=n).mean().replace(0,np.nan)
    return 100-(100/(1+rs))

def true_range(df: pd.DataFrame):
    pc=df['Close'].shift(1)
    return pd.concat([(df['High']-df['Low']).abs(),(df['High']-pc).abs(),(df['Low']-pc).abs()],axis=1).max(axis=1)

def atr(df: pd.DataFrame,n=14):
    return true_range(df).ewm(alpha=1/n,adjust=False,min_periods=n).mean()

def indicator_frame(df: pd.DataFrame):
    out=df.copy()
    c=out['Close'].astype(float)
    h=out['High'].astype(float)
    l=out['Low'].astype(float)
    v=out.get('Volume',pd.Series(0,index=out.index,dtype=float)).fillna(0).astype(float)

    for n in (20,50,200):
        out[f'MA{n}']=c.rolling(n).mean()
        out[f'EMA{n}']=c.ewm(span=n,adjust=False,min_periods=min(n,len(c))).mean()

    out['RSI14']=rsi(c,14)
    rmin=out['RSI14'].rolling(14).min()
    rmax=out['RSI14'].rolling(14).max()
    stoch=((out['RSI14']-rmin)/(rmax-rmin).replace(0,np.nan))*100
    out['STOCH_RSI_K']=stoch.rolling(3).mean()
    out['STOCH_RSI_D']=out['STOCH_RSI_K'].rolling(3).mean()

    ema12=c.ewm(span=12,adjust=False,min_periods=12).mean()
    ema26=c.ewm(span=26,adjust=False,min_periods=26).mean()
    out['MACD']=ema12-ema26
    out['MACD_SIGNAL']=out['MACD'].ewm(span=9,adjust=False,min_periods=9).mean()
    out['MACD_HIST']=out['MACD']-out['MACD_SIGNAL']

    mid=c.rolling(20).mean()
    std=c.rolling(20).std()
    out['BB_MID']=mid
    out['BB_UPPER']=mid+2*std
    out['BB_LOWER']=mid-2*std
    out['BB_WIDTH']=((out['BB_UPPER']-out['BB_LOWER'])/mid.replace(0,np.nan))*100
    out['BB_PCT']=((c-out['BB_LOWER'])/(out['BB_UPPER']-out['BB_LOWER']).replace(0,np.nan))*100

    out['ATR14']=atr(out,14)
    out['ATR_PCT']=out['ATR14']/c.replace(0,np.nan)*100

    up_move=h.diff()
    down_move=-l.diff()
    plus_dm=pd.Series(np.where((up_move>down_move)&(up_move>0),up_move,0.0),index=out.index)
    minus_dm=pd.Series(np.where((down_move>up_move)&(down_move>0),down_move,0.0),index=out.index)
    atr14=out['ATR14'].replace(0,np.nan)
    plus_di=100*plus_dm.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr14
    minus_di=100*minus_dm.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr14
    dx=100*(plus_di-minus_di).abs()/(plus_di+minus_di).replace(0,np.nan)
    out['PLUS_DI']=plus_di
    out['MINUS_DI']=minus_di
    out['ADX14']=dx.ewm(alpha=1/14,adjust=False,min_periods=14).mean()

    typical=(h+l+c)/3
    money=typical*v
    direction=typical.diff()
    pos=pd.Series(np.where(direction>0,money,0.0),index=out.index)
    neg=pd.Series(np.where(direction<0,money,0.0),index=out.index)
    mr=pos.rolling(14).sum()/neg.rolling(14).sum().replace(0,np.nan)
    out['MFI14']=100-(100/(1+mr))

    signed=np.sign(c.diff()).fillna(0)
    out['OBV']=(signed*v).cumsum()
    vol20=v.rolling(20).mean().replace(0,np.nan)
    out['OBV_TREND20']=(out['OBV']-out['OBV'].shift(20))/(vol20*20)

    return out

def score_frame(df: pd.DataFrame, benchmark_return_20=0.0, benchmark_return_60=0.0):
    df=df.dropna(subset=['Close']).copy()
    if len(df)<30:
        return None
    x=indicator_frame(df)
    c=x['Close'].astype(float)
    v=x.get('Volume',pd.Series(index=x.index,dtype=float)).fillna(0).astype(float)
    last=_num(c.iloc[-1])
    prev=_num(c.iloc[-2],last)
    ma20=x['MA20']; ma50=x['MA50']; ma200=x['MA200']
    ema20=x['EMA20']; ema50=x['EMA50']; ema200=x['EMA200']
    vol20=v.rolling(20).mean()

    mom5=(last/_num(c.iloc[-6],last)-1)*100 if len(c)>=6 else 0
    mom20=(last/_num(c.iloc[-21],last)-1)*100 if len(c)>=21 else 0
    mom60=(last/_num(c.iloc[-61],last)-1)*100 if len(c)>=61 else mom20
    mom120=(last/_num(c.iloc[-121],last)-1)*100 if len(c)>=121 else mom60
    rs20=mom20-_num(benchmark_return_20)
    rs60=mom60-_num(benchmark_return_60)

    r=_num(x['RSI14'].iloc[-1],50)
    sk=_num(x['STOCH_RSI_K'].iloc[-1],50)
    sd=_num(x['STOCH_RSI_D'].iloc[-1],50)
    macd=_num(x['MACD'].iloc[-1])
    macds=_num(x['MACD_SIGNAL'].iloc[-1])
    mach=_num(x['MACD_HIST'].iloc[-1])
    adx=_num(x['ADX14'].iloc[-1],20)
    pdi=_num(x['PLUS_DI'].iloc[-1])
    mdi=_num(x['MINUS_DI'].iloc[-1])
    mfi=_num(x['MFI14'].iloc[-1],50)
    atrv=_num(x['ATR14'].iloc[-1],last*.03)
    atrpct=_num(x['ATR_PCT'].iloc[-1],3)
    bbpct=_num(x['BB_PCT'].iloc[-1],50)
    bbwidth=_num(x['BB_WIDTH'].iloc[-1],0)
    obvt=_num(x['OBV_TREND20'].iloc[-1],0)
    vr=_num(v.iloc[-1]/vol20.iloc[-1],1) if len(vol20) else 1
    hi20=_num(c.shift(1).rolling(20).max().iloc[-1],last)
    breakout=last>hi20 if hi20 else False
    volat=_num(c.pct_change().tail(20).std()*np.sqrt(252)*100,0)

    short=48
    short += 10 if last>_num(ema20.iloc[-1],last) else -9
    short += 8 if _num(ema20.iloc[-1])>_num(ema50.iloc[-1]) else -7
    short += max(-8,min(10,mom20*.55))
    short += max(-5,min(7,(vr-1)*7))
    short += 7 if breakout else 0
    short += 5 if mach>0 and macd>macds else -4 if mach<0 and macd<macds else 0
    short += 5 if adx>=25 and pdi>mdi else -3 if adx>=25 and mdi>pdi else 0
    short += 4 if sk>sd and sk<80 else -3 if sk<sd and sk>20 else 0
    short += 4 if 45<=r<=68 else (-7 if r>82 else -2 if r<30 else 0)
    short += max(-5,min(6,rs20*.25))
    short += 3 if obvt>0.05 else -2 if obvt<-0.05 else 0
    if mfi>85: short-=4
    if bbpct>105: short+=2 if vr>1.3 else -2
    short=int(max(0,min(100,round(short))))

    long=48
    if len(c)>=200:
        long += 13 if last>_num(ema200.iloc[-1]) else -13
    long += 10 if _num(ema50.iloc[-1])>_num(ema200.iloc[-1],_num(ema50.iloc[-1])) else -7
    long += max(-10,min(14,mom120*.30))
    long += max(-7,min(10,mom60*.20))
    long += max(-5,min(7,rs60*.18))
    long += 4 if adx>=22 and pdi>mdi else -3 if adx>=25 and mdi>pdi else 0
    long += 3 if obvt>0 else -2
    long -= max(0,min(11,(volat-35)*.23))
    long=int(max(0,min(100,round(long))))

    risk=int(max(0,min(100,round(volat*1.15+atrpct*4))))
    gap=abs((last/prev-1)*100) if prev else 0
    anomaly=int(max(0,min(100,round(max(0,vr-1)*24+max(0,gap-3)*6+max(0,volat-45)*.7))))
    smart=int(max(0,min(100,round(50+(10 if last>_num(ema20.iloc[-1]) else -9)+max(-12,min(18,(vr-1)*12))+max(-10,min(15,mom20*.35))+max(-7,min(7,obvt*18))))))
    alpha=int(max(0,min(100,round(short*.50+long*.42+max(-8,min(8,rs20*.2))-risk*.10))))

    reasons_short=[]
    if breakout: reasons_short.append('20G breakout')
    if mach>0 and macd>macds: reasons_short.append('MACD pozitif')
    if adx>=25 and pdi>mdi: reasons_short.append(f'ADX {adx:.0f} güçlü trend')
    if sk>sd and sk<80: reasons_short.append('Stoch RSI yukarı')
    if rs20>3: reasons_short.append(f'XU100 göre +%{rs20:.1f}')
    if vr>1.5: reasons_short.append(f'hacim {vr:.1f}x')
    if not reasons_short and last>_num(ema20.iloc[-1]): reasons_short.append('EMA20 üstü')

    reasons_long=[]
    if len(c)>=200 and last>_num(ema200.iloc[-1]): reasons_long.append('EMA200 üstü')
    if _num(ema50.iloc[-1])>_num(ema200.iloc[-1],_num(ema50.iloc[-1])): reasons_long.append('EMA50/200 pozitif')
    if rs60>5: reasons_long.append(f'3A relative strength +%{rs60:.1f}')
    if mom120>10: reasons_long.append(f'6A momentum +%{mom120:.1f}')
    if adx>=25 and pdi>mdi: reasons_long.append('trend gücü yüksek')

    return {
      'price':round(last,2),'change':round((last/prev-1)*100,2) if prev else 0,
      'short_score':short,'long_score':long,'alpha_score':alpha,
      'short_signal':'GÜÇLÜ' if short>=80 else 'POZİTİF' if short>=68 else 'NÖTR' if short>=48 else 'ZAYIF',
      'long_signal':'GÜÇLÜ' if long>=80 else 'POZİTİF' if long>=68 else 'NÖTR' if long>=48 else 'ZAYIF',
      'rsi':round(r,1),'stoch_rsi_k':round(sk,1),'stoch_rsi_d':round(sd,1),
      'macd':round(macd,4),'macd_signal':round(macds,4),'macd_hist':round(mach,4),
      'adx':round(adx,1),'plus_di':round(pdi,1),'minus_di':round(mdi,1),
      'mfi':round(mfi,1),'atr':round(atrv,4),'atr_pct':round(atrpct,2),
      'bb_pct':round(bbpct,1),'bb_width':round(bbwidth,2),'obv_trend':round(obvt,3),
      'relative_strength_20':round(rs20,2),'relative_strength_60':round(rs60,2),
      'volume_ratio':round(vr,2),'momentum_5':round(mom5,2),'momentum_20':round(mom20,2),
      'momentum_60':round(mom60,2),'momentum_120':round(mom120,2),
      'volatility':round(volat,1),'risk':risk,'anomaly_score':anomaly,'smart_money_score':smart,
      'breakout20':bool(breakout),
      'trend':'YUKARI' if last>_num(ema20.iloc[-1])>_num(ema50.iloc[-1]) else 'AŞAĞI' if last<_num(ema20.iloc[-1])<_num(ema50.iloc[-1]) else 'YATAY',
      'target_short':round(last+2*atrv,2),'stop_short':round(max(0,last-1.4*atrv),2),
      'reasons_short':reasons_short[:4],'reasons_long':reasons_long[:4],
      'spark':[round(_num(z),2) for z in c.tail(30).tolist()]
    }
