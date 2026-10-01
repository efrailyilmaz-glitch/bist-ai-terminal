from __future__ import annotations
import json, math, os, platform, threading, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
from .market_data import yahoo_rows, scan_codes
from .universe import get_universe

_LOCK=threading.Lock();TTL=6*3600;SCHEMA_VERSION=3
def _dir():
    if platform.system()=='Darwin':b=Path.home()/'Library'/'Application Support'/'BIST AI Terminal'
    elif platform.system()=='Windows':b=Path(os.getenv('APPDATA') or Path.home())/'BIST AI Terminal'
    else:b=Path.home()/'.bist-ai-terminal'
    b.mkdir(parents=True,exist_ok=True);return b
def _file():return _dir()/'cycle_profiles.json'
_CACHE={}
def _load():
    global _CACHE
    try:
        p=_file()
        if p.exists():_CACHE=json.loads(p.read_text(encoding='utf-8'))
    except Exception:_CACHE={}
def _save():
    try:_file().write_text(json.dumps(_CACHE,ensure_ascii=False),encoding='utf-8')
    except Exception:pass
_load()
def _rows(ticker,period='10y'):
    rows=yahoo_rows(ticker,period=period,interval='1d').get('candles') or []
    if not rows:return None
    df=pd.DataFrame(rows);df['date']=pd.to_datetime(df['time'],errors='coerce');df['close']=pd.to_numeric(df['close'],errors='coerce')
    return df.dropna(subset=['date','close']).sort_values('date').set_index('date')
def _fwd(c,n):
    return (c.shift(-n)/c-1)*100
def _seasonality(df):
    m=df.close.resample('ME').last().pct_change()*100
    # Do not contaminate historical month statistics with the current partial month.
    now=pd.Timestamp.today()
    if len(m) and m.index[-1].year==now.year and m.index[-1].month==now.month:m=m.iloc[:-1]
    out=[]
    for month in range(1,13):
        x=m[m.index.month==month].dropna()
        if len(x)<3:continue
        out.append({'month':month,'n':int(len(x)),'mean':round(float(x.mean()),2),'median':round(float(x.median()),2),'positive':round(float((x>0).mean()*100),1),'std':round(float(x.std()),2)})
    return out
def _cycle_candidates(df):
    c=df.close;ret=c.pct_change().dropna()
    periods=[10,15,20,30,40,60,90,120]
    out=[]
    for p in periods:
        if len(ret)<p*4:continue
        # autocorrelation of returns and rolling p-day outcome consistency
        ac=float(ret.autocorr(lag=p)) if len(ret)>p+20 else 0
        fr=_fwd(c,p).dropna()
        if len(fr)<25:continue
        hit=float((fr>0).mean()*100);med=float(fr.median());mean=float(fr.mean())
        # phase test: compare current p-position using recent local extrema
        look=min(len(c)-1,p*4)
        sub=c.tail(look)
        min_i=int(np.argmin(sub.values));max_i=int(np.argmax(sub.values))
        since_low=len(sub)-1-min_i;since_high=len(sub)-1-max_i
        out.append({'period':p,'autocorr':round(ac,3),'n':int(len(fr)),'positive_pct':round(hit,1),'median_return_pct':round(med,2),'mean_return_pct':round(mean,2),
                    'since_recent_low':since_low,'since_recent_high':since_high})
    return out
def _regularity(season,cycles):
    ss=0.0
    if season:
        best=max(season,key=lambda x:abs(x['positive']-50))
        # Reward a month that behaves consistently across years.
        ss+=min(38,abs(best['positive']-50)*1.5)
        if best.get('n',0)>=6:ss+=4
    if cycles:
        best=max(cycles,key=lambda x:abs(x['autocorr']))
        # Autocorrelation strength + directional consistency of the same horizon.
        ss+=min(32,abs(best['autocorr'])*100)
        ss+=min(18,abs(best.get('positive_pct',50)-50)*.72)
        # Conflicting horizon outcomes are noise, not regularity.
        dispersion=float(np.std([x['median_return_pct'] for x in cycles])) if len(cycles)>2 else 0
        ss-=min(14,dispersion*.45)
    return round(max(0,min(100,ss)))
def cycle_profile(ticker,force=False):
    code=ticker.upper().replace('.IS','');now=time.time()
    with _LOCK:
        h=_CACHE.get(code)
        if h and h.get('_schema')==SCHEMA_VERSION and h.get('history_period')=='10y' and not force and now-float(h.get('_ts',0))<TTL:return h
    df=_rows(code,'10y')
    if df is None or len(df)<260:return {'ticker':code,'status':'NO_DATA'}
    season=_seasonality(df);cycles=_cycle_candidates(df);regularity=_regularity(season,cycles)
    month=int(pd.Timestamp.today().month)
    sm=next((x for x in season if x['month']==month),None)
    best_cycle=max(cycles,key=lambda x:abs(x['autocorr'])) if cycles else None
    tech=(scan_codes([code]) or [{}])[0]
    score=50;reasons=[]
    if sm:
        score+=(sm['positive']-50)*.45
        if sm['positive']>=65 and sm['median']>0:reasons.append(f"{month}. ay tarihsel olarak güçlü: %{sm['positive']} pozitif")
        if sm['positive']<=35 and sm['median']<0:reasons.append(f"{month}. ay tarihsel olarak zayıf: %{sm['positive']} pozitif")
    if best_cycle and abs(best_cycle['autocorr'])>=.12:
        score+=best_cycle['autocorr']*35
        reasons.append(f"{best_cycle['period']} işlem günlük döngüde tekrar sinyali")
    short=float(tech.get('short_score') or 50);long=float(tech.get('long_score') or 50);risk=float(tech.get('risk') or 50)
    score+=(short-50)*.20+(long-50)*.10-(risk-50)*.08
    score=max(0,min(100,round(score)))
    if regularity<30:signal='NÖTR'
    elif score>=67 and short>=58:signal='ALIM_PENCERESİ'
    elif score<=38 or (sm and sm['positive']<=35 and short<48):signal='SATIŞ_RİSKİ'
    elif score<50 and risk>=65:signal='KÂR_KORUMA'
    else:signal='NÖTR'
    confidence=round(min(100,regularity*.65+(abs(score-50)*1.1)))
    out={'ticker':code,'status':'OK','signal':signal,'cycle_score':score,'regularity_score':regularity,'confidence':confidence,'seasonality':season,'cycles':cycles,
         'current_month':month,'current_month_stats':sm,'dominant_cycle':best_cycle,'technical':{'short_score':short,'long_score':long,'risk':risk},
         'reasons':reasons[:5],'years':round((df.index[-1]-df.index[0]).days/365.25,1),'history_period':'10y','_schema':SCHEMA_VERSION,'_ts':now,
         'note':'Cycle/seasonality signals are historical statistical patterns, not deterministic buy/sell instructions. Current technical confirmation is required.'}
    with _LOCK:_CACHE[code]=out;_save()
    return out
def cycle_radar(limit=40):
    with _LOCK:rows=[v for v in _CACHE.values() if isinstance(v,dict) and v.get('status')=='OK']
    cap=max(5,min(int(limit),100));sell_quota=max(3,min(10,cap//4))
    buys=sorted([x for x in rows if x.get('signal')=='ALIM_PENCERESİ'],key=lambda x:(-x.get('regularity_score',0),-x.get('confidence',0)))
    others=sorted([x for x in rows if x.get('signal') not in {'ALIM_PENCERESİ','SATIŞ_RİSKİ'}],key=lambda x:(-x.get('regularity_score',0),-x.get('confidence',0)))
    sells=sorted([x for x in rows if x.get('signal')=='SATIŞ_RİSKİ'],key=lambda x:(-x.get('confidence',0),-x.get('regularity_score',0)))
    chosen=(buys+others)[:max(1,cap-min(sell_quota,len(sells)))]+sells[:sell_quota]
    return {'rows':chosen,'analyzed':len(rows),'universe':len(get_universe()),'note':'Background scanner gradually covers the full BIST universe and reserves shortlist capacity for both buy-window and sell-risk patterns.'}
_CURSOR=0
def scan_cycle_batch(batch=24):
    global _CURSOR
    u=get_universe()
    if not u:return {'scanned':0}
    n=max(5,min(int(batch),50));codes=[]
    for _ in range(n):
        codes.append(u[_CURSOR%len(u)]['ticker']);_CURSOR+=1
    done=0
    def one(code):
        try:
            x=cycle_profile(code,force=False)
            return 1 if x.get('status')=='OK' else 0
        except Exception:return 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        done=sum(ex.map(one,codes))
    return {'scanned':done,'cursor':_CURSOR,'universe':len(u)}
