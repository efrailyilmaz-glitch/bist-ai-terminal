from __future__ import annotations
import math, time, threading
import numpy as np
import pandas as pd
from .market_data import yahoo_rows, scan_codes
from .pro_tools import technical_pro

_LOCK=threading.Lock();_CACHE={};TTL=10*60
def _v(x,d=None):
    try:
        if x is None:return d
        z=float(x);return d if math.isnan(z) or math.isinf(z) else z
    except Exception:return d
def _frame(ticker,period='2y'):
    rows=yahoo_rows(ticker,period=period,interval='1d').get('candles') or []
    if not rows:return None
    df=pd.DataFrame(rows).rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
    for c in ['Open','High','Low','Close','Volume']:df[c]=pd.to_numeric(df[c],errors='coerce')
    return df.dropna(subset=['Close']).reset_index(drop=True)
def decision_levels(ticker):
    code=ticker.upper().replace('.IS','');key='levels:'+code;now=time.time()
    with _LOCK:
        h=_CACHE.get(key)
        if h and now-h[0]<TTL:return h[1]
    df=_frame(code,'2y');tech=(scan_codes([code]) or [{}])[0]
    if df is None or len(df)<80 or not tech:return {'ticker':code,'status':'NO_DATA'}
    c=df.Close;h=df.High;l=df.Low;v=df.Volume.fillna(0);price=float(c.iloc[-1])
    pc=c.shift(1);tr=pd.concat([(h-l).abs(),(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1);atr=float(tr.ewm(alpha=1/14,adjust=False).mean().iloc[-1])
    # transparent swing levels
    low20=float(l.tail(20).min());low60=float(l.tail(60).min());low120=float(l.tail(120).min())
    high20=float(h.tail(20).max());high60=float(h.tail(60).max());high120=float(h.tail(120).max())
    supports=sorted({round(x,4) for x in (tech.get('supports') or [])+[low20,low60]},reverse=True)
    supports=[x for x in supports if x<price]
    resist=sorted({round(x,4) for x in (tech.get('resistances') or [])+[high20,high60]})
    resist=[x for x in resist if x>price]
    pro=technical_pro(code)
    avwap=_v(pro.get('anchored_vwap'));vwap=_v(pro.get('vwap20'))
    # volume-by-price approximation from daily OHLCV typical price
    sub=df.tail(120).copy();typ=(sub.High+sub.Low+sub.Close)/3
    bins=np.linspace(float(sub.Low.min()),float(sub.High.max()),25)
    ids=np.clip(np.digitize(typ,bins)-1,0,len(bins)-2)
    vp=np.zeros(len(bins)-1)
    for i,vol in zip(ids,sub.Volume.fillna(0)):vp[int(i)]+=float(vol)
    centers=(bins[:-1]+bins[1:])/2
    below=[(centers[i],vp[i]) for i in range(len(vp)) if centers[i]<price]
    vp_support=max(below,key=lambda x:x[1])[0] if below else None
    dip_candidates=[x for x in supports[:3] if x>0]
    if avwap and avwap<price:dip_candidates.append(avwap)
    if vwap and vwap<price:dip_candidates.append(vwap)
    if vp_support and vp_support<price:dip_candidates.append(vp_support)
    dip_candidates=[x for x in dip_candidates if price*.65<x<price]
    center=float(np.median(dip_candidates)) if dip_candidates else max(price-2.2*atr,0)
    dip_low=max(0,min(center-0.65*atr,price-1.2*atr))
    dip_high=min(price,center+0.45*atr)
    breakout=(resist[0] if resist else high20)+0.15*atr
    stop_ref=max(0,(supports[0] if supports else price-1.6*atr)-0.25*atr)
    hard_stop=max(0,(supports[1] if len(supports)>1 else price-2.5*atr)-0.2*atr)
    short_t=(resist[0] if resist else price+1.8*atr)
    med_t=max(resist[1] if len(resist)>1 else 0,price+3.5*atr)
    long_t=max(high120,price+6.0*atr)
    trend_down=bool(tech.get('trend')=='AŞAĞI' or (tech.get('supertrend')=='BEARISH' and tech.get('ichimoku')=='BEARISH'))
    dip_conf=50
    dip_conf+=12 if len(dip_candidates)>=3 else 5 if len(dip_candidates)>=2 else 0
    dip_conf+=8 if vp_support and dip_low<=vp_support<=dip_high else 0
    dip_conf+=8 if avwap and dip_low<=avwap<=dip_high else 0
    dip_conf+=5 if _v(tech.get('rsi'),50)<40 else 0
    dip_conf-=10 if _v(tech.get('volume_ratio'),1)>1.8 and _v(tech.get('change'),0)<-3 else 0
    dip_conf=max(0,min(100,round(dip_conf)))
    out={'ticker':code,'status':'OK','price':round(price,2),'atr':round(atr,2),
         'short_target':round(short_t,2),'medium_target':round(med_t,2),'long_target':round(long_t,2),
         'breakout_confirmation':round(breakout,2),'stop_reference':round(stop_ref,2),'hard_invalidation':round(hard_stop,2),
         'dip_zone_low':round(dip_low,2),'dip_zone_high':round(dip_high,2),'dip_zone_confidence':dip_conf,'trend_down':trend_down,
         'guidance':{
           'breakout':f'₺{breakout:.2f} üzeri kapanış/kırılım, yukarı senaryonun teknik teyit bölgesidir.',
           'dip':f'₺{dip_low:.2f}–₺{dip_high:.2f} aralığı destek/ATR/AVWAP/hacim profilinin birleştiği olası tepki bölgesidir; kesin dip değildir.',
           'stop':f'₺{stop_ref:.2f} altı kısa vadeli tezi zayıflatır. ₺{hard_stop:.2f} altı daha güçlü teknik geçersizlik referansıdır.',
           'targets':'Hedefler garanti fiyat değil; mevcut volatilite ve teknik dirençlere göre araştırma senaryolarıdır.'
         },
         'note':'Decision Levels are research references, not deterministic buy/sell instructions. Use closing-price confirmation and liquidity/slippage checks.'}
    with _LOCK:_CACHE[key]=(now,out)
    return out
