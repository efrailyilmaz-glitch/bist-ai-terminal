from __future__ import annotations
import json, math, os, platform, threading, time
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
from .market_data import yahoo_rows
from .scoring import indicator_frame
from .universe import get_universe

_LOCK=threading.Lock();_CACHE={};TTL=30*60;PERSIST_TTL=6*3600;SCHEMA_VERSION=3
def _store_dir():
    from pathlib import Path
    if platform.system()=='Darwin':b=Path.home()/'Library'/'Application Support'/'BIST AI Terminal'
    elif platform.system()=='Windows':b=Path(os.getenv('APPDATA') or Path.home())/'BIST AI Terminal'
    else:b=Path.home()/'.bist-ai-terminal'
    b.mkdir(parents=True,exist_ok=True);return b
def _store_file():return _store_dir()/'weekly_reversal_profiles.json'
_PERSIST={}
def _load_persist():
    global _PERSIST
    try:
        p=_store_file()
        if p.exists():_PERSIST=json.loads(p.read_text(encoding='utf-8'))
    except Exception:_PERSIST={}
def _save_persist():
    try:_store_file().write_text(json.dumps(_PERSIST,ensure_ascii=False),encoding='utf-8')
    except Exception:pass
_load_persist()
_SCAN_CURSOR=int((_PERSIST.get('__meta__') or {}).get('cursor',0)) if isinstance(_PERSIST.get('__meta__'),dict) else 0

def _v(x,d=None):
    try:
        if x is None:return d
        z=float(x);return d if math.isnan(z) or math.isinf(z) else z
    except Exception:return d

def _df(code,period='5y'):
    rows=(yahoo_rows(code,period=period,interval='1wk').get('candles') or [])
    if not rows:return None
    df=pd.DataFrame(rows).rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
    for c in ['Open','High','Low','Close','Volume']:df[c]=pd.to_numeric(df[c],errors='coerce')
    return df.dropna(subset=['Close']).reset_index(drop=True)

def _week_is_open(df):
    try:
        last=pd.to_datetime(df.iloc[-1].get('time'),errors='coerce')
        if pd.isna(last):return False
        now=datetime.now(ZoneInfo('Europe/Istanbul'))
        same_week=(last.isocalendar().year==now.isocalendar().year and last.isocalendar().week==now.isocalendar().week)
        if not same_week:return False
        return now.weekday()<4 or (now.weekday()==4 and (now.hour<18 or (now.hour==18 and now.minute<15)))
    except Exception:return False

def _provisional_snapshot(df):
    try:
        ind=indicator_frame(df);r=ind.iloc[-1]
        return {'time':str(df.iloc[-1].get('time')),'rsi':round(_v(r.get('RSI14'),50),1),'stoch_k':round(_v(r.get('STOCH_RSI_K'),50),1),
                'stoch_d':round(_v(r.get('STOCH_RSI_D'),50),1),'macd_hist':round(_v(r.get('MACD_HIST'),0),4),
                'note':'Current weekly candle is still open and is not used for confirmed ranking or alerts.'}
    except Exception:return None

def _weekly_features(code):
    raw=_df(code,'5y')
    if raw is None or len(raw)<60:return None
    week_open=_week_is_open(raw);provisional=_provisional_snapshot(raw) if week_open else None
    df=raw.iloc[:-1].copy().reset_index(drop=True) if week_open and len(raw)>60 else raw
    if len(df)<60:return None
    ind=indicator_frame(df)
    c=df.Close.astype(float);v=df.Volume.fillna(0).astype(float)
    rsi=ind.RSI14;sk=ind.STOCH_RSI_K;sd=ind.STOCH_RSI_D;mh=ind.MACD_HIST;macd=ind.MACD;ms=ind.MACD_SIGNAL
    ema20=ind.EMA20;ema50=ind.EMA50;adx=ind.ADX14;pdi=ind.PLUS_DI;mdi=ind.MINUS_DI
    vol13=v.rolling(13).mean().replace(0,np.nan)
    vol_ratio=_v(v.iloc[-1]/vol13.iloc[-1],1)
    rsi_now=_v(rsi.iloc[-1],50);rsi_prev=_v(rsi.iloc[-2],rsi_now);rsi3=_v(rsi.iloc[-4],rsi_prev)
    rsi_min6=_v(rsi.tail(6).min(),rsi_now)
    rsi_turn=rsi_now>rsi_prev and rsi_prev>=rsi3-2 and rsi_min6<=45
    stoch_cross=_v(sk.iloc[-1],50)>_v(sd.iloc[-1],50) and _v(sk.iloc[-2],50)<=_v(sd.iloc[-2],50)
    stoch_low_cross=stoch_cross and min(_v(sk.iloc[-2],50),_v(sd.iloc[-2],50))<=35
    macd_green=_v(mh.iloc[-1],0)>0
    macd_new_green=macd_green and _v(mh.iloc[-2],0)<=0
    macd_rising=_v(mh.iloc[-1],0)>_v(mh.iloc[-2],0)>_v(mh.iloc[-3],0)
    macd_cross=_v(macd.iloc[-1],0)>_v(ms.iloc[-1],0) and _v(macd.iloc[-2],0)<=_v(ms.iloc[-2],0)
    price=float(c.iloc[-1]);e20=_v(ema20.iloc[-1],price);e50=_v(ema50.iloc[-1],price)
    ema20_reclaim=price>e20 and float(c.iloc[-2])<=_v(ema20.iloc[-2],float(c.iloc[-2]))
    ema20_slope=_v(ema20.iloc[-1]-ema20.iloc[-3],0)
    trend_ok=price>e20 and ema20_slope>=0
    plusdi_ok=_v(pdi.iloc[-1],0)>_v(mdi.iloc[-1],0)
    adx_ok=_v(adx.iloc[-1],0)>=18
    higher_low=float(df.Low.iloc[-1])>float(df.Low.iloc[-3]) if len(df)>=4 else False
    # benchmark relative strength over 4 and 12 weeks
    rs4=rs12=0.0
    try:
        b=_df('XU100','5y')
        if b is not None and _week_is_open(b) and len(b)>13:b=b.iloc[:-1].copy().reset_index(drop=True)
        if b is not None and len(b)>=13:
            a4=(c.iloc[-1]/c.iloc[-5]-1)*100;b4=(b.Close.iloc[-1]/b.Close.iloc[-5]-1)*100
            a12=(c.iloc[-1]/c.iloc[-13]-1)*100;b12=(b.Close.iloc[-1]/b.Close.iloc[-13]-1)*100
            rs4=float(a4-b4);rs12=float(a12-b12)
    except Exception:pass
    score=0
    score+=18 if rsi_turn else 0
    score+=8 if rsi_min6<=35 else 4 if rsi_min6<=45 else 0
    score+=18 if stoch_low_cross else 10 if stoch_cross else 4 if _v(sk.iloc[-1],50)>_v(sd.iloc[-1],50) and _v(sk.iloc[-1],50)<55 else 0
    score+=22 if macd_new_green else 14 if macd_cross else 8 if macd_green and macd_rising else 0
    score+=12 if ema20_reclaim else 7 if trend_ok else 0
    score+=6 if plusdi_ok else 0
    score+=4 if adx_ok else 0
    score+=5 if vol_ratio>=1.2 else 2 if vol_ratio>=1.0 else 0
    score+=5 if rs4>0 and rs4>rs12/3 else 0
    score+=4 if higher_low else 0
    score=min(100,round(score))
    if score>=78 and macd_green and (stoch_cross or stoch_low_cross) and rsi_turn and trend_ok:signal='ALIM_PENCERESİ'
    elif score>=65 and rsi_turn and (macd_new_green or macd_rising):signal='ERKEN_DÖNÜŞ'
    elif score>=52:signal='TEYİT_BEKLE'
    elif _v(mh.iloc[-1],0)<0 and rsi_now<rsi_prev and _v(sk.iloc[-1],50)<_v(sd.iloc[-1],50):signal='SATIŞ_RİSKİ'
    else:signal='NÖTR'
    return {'ticker':code,'status':'OK','signal':signal,'score':score,'price':round(price,2),'rsi':round(rsi_now,1),'rsi_min6':round(rsi_min6,1),
            'rsi_rising':bool(rsi_turn),'stoch_k':round(_v(sk.iloc[-1],50),1),'stoch_d':round(_v(sd.iloc[-1],50),1),'stoch_low_cross':bool(stoch_low_cross),
            'macd_hist':round(_v(mh.iloc[-1],0),4),'macd_new_green':bool(macd_new_green),'macd_rising':bool(macd_rising),'macd_cross':bool(macd_cross),
            'ema20':round(e20,2),'ema50':round(e50,2),'ema20_reclaim':bool(ema20_reclaim),'trend_ok':bool(trend_ok),'adx':round(_v(adx.iloc[-1],0),1),
            'plus_di':round(_v(pdi.iloc[-1],0),1),'minus_di':round(_v(mdi.iloc[-1],0),1),'volume_ratio':round(vol_ratio,2),
            'rs4':round(rs4,2),'rs12':round(rs12,2),'higher_low':bool(higher_low),'bars':len(df),'bar_status':'CONFIRMED_CLOSED_WEEK',
            'provisional':provisional,'_df':df,'_ind':ind}

def _historical_setup_stats(base):
    df=base.pop('_df');ind=base.pop('_ind')
    c=df.Close.astype(float);v=df.Volume.fillna(0).astype(float);vol13=v.rolling(13).mean().replace(0,np.nan)
    events=[]
    for i in range(55,len(df)-13):
        rsi=ind.RSI14;sk=ind.STOCH_RSI_K;sd=ind.STOCH_RSI_D;mh=ind.MACD_HIST;ema20=ind.EMA20
        rnow=_v(rsi.iloc[i],50);rprev=_v(rsi.iloc[i-1],rnow);r3=_v(rsi.iloc[i-3],rprev);rmin=_v(rsi.iloc[max(0,i-5):i+1].min(),rnow)
        rt=rnow>rprev and rprev>=r3-2 and rmin<=45
        sc=_v(sk.iloc[i],50)>_v(sd.iloc[i],50) and _v(sk.iloc[i-1],50)<=_v(sd.iloc[i-1],50) and min(_v(sk.iloc[i-1],50),_v(sd.iloc[i-1],50))<=35
        mg=_v(mh.iloc[i],0)>0 and _v(mh.iloc[i-1],0)<=0
        tr=float(c.iloc[i])>_v(ema20.iloc[i],float(c.iloc[i])) and _v(ema20.iloc[i]-ema20.iloc[i-2],0)>=0
        if rt and sc and mg:
            p=float(c.iloc[i]);e={'r4':None,'r8':None,'r12':None,'trend_confirm':tr}
            for n in (4,8,12):
                if i+n<len(c):e[f'r{n}']=(float(c.iloc[i+n])/p-1)*100
            events.append(e)
    def s(n,trend_only=False):
        xs=[e[f'r{n}'] for e in events if e[f'r{n}'] is not None and (not trend_only or e.get('trend_confirm'))]
        if not xs:return {'n':0}
        return {'n':len(xs),'positive_pct':round(sum(1 for x in xs if x>0)/len(xs)*100,1),'mean_pct':round(float(np.mean(xs)),2),'median_pct':round(float(np.median(xs)),2)}
    return {'events':len(events),'4w':s(4),'8w':s(8),'12w':s(12),
            'trend_confirmed':{'4w':s(4,True),'8w':s(8,True),'12w':s(12,True)},
            'note':'Core setup = weekly RSI rising from <=45 + low Stoch RSI bullish cross + MACD histogram newly positive. Trend-confirmed subset also requires price above a rising weekly EMA20.'}

def _public(base):
    return {k:v for k,v in base.items() if not k.startswith('_')}

def weekly_reversal(ticker,with_history=True):
    code=ticker.upper().replace('.IS','');key=f'{code}:{int(bool(with_history))}';now=time.time()
    with _LOCK:
        hit=_CACHE.get(key)
        if hit and now-hit[0]<TTL:return hit[1]
        ph=_PERSIST.get(code)
        if (not with_history) and ph and ph.get('_schema')==SCHEMA_VERSION and now-float(ph.get('_ts',0))<PERSIST_TTL:
            return _public(ph)
    base=_weekly_features(code)
    if not base:return {'ticker':code,'status':'NO_DATA'}
    if with_history:
        hist=_historical_setup_stats(base)
    else:
        base.pop('_df',None);base.pop('_ind',None);hist=None
    base['historical']=hist
    base['note']='Weekly reversal is a research signal. False positives are reduced with EMA20, DI/ADX, volume and XU100 relative-strength confirmation.'
    public=_public(base)
    with _LOCK:
        _CACHE[key]=(now,public)
        if not with_history:
            _PERSIST[code]={**public,'_schema':SCHEMA_VERSION,'_ts':now}
            _save_persist()
    return public

def scan_weekly_reversal_batch(batch=24):
    global _SCAN_CURSOR
    u=get_universe()
    if not u:return {'scanned':0,'universe':0}
    n=max(5,min(int(batch),50));codes=[]
    for _ in range(n):
        codes.append(u[_SCAN_CURSOR%len(u)]['ticker']);_SCAN_CURSOR+=1
    done=0
    with ThreadPoolExecutor(max_workers=5) as ex:
        for x in ex.map(lambda c:weekly_reversal(c,with_history=False),codes):
            if x.get('status')=='OK':done+=1
    with _LOCK:
        _PERSIST['__meta__']={'cursor':_SCAN_CURSOR,'updated_at':time.time()}
        _save_persist()
    return {'scanned':done,'cursor':_SCAN_CURSOR,'universe':len(u)}

def weekly_reversal_radar(limit=60,universe_limit=0):
    u=get_universe();now=time.time()
    with _LOCK:
        rows=[_public(v) for k,v in _PERSIST.items() if k!='__meta__' and isinstance(v,dict) and v.get('_schema')==SCHEMA_VERSION and now-float(v.get('_ts',0))<PERSIST_TTL and v.get('status')=='OK']
    # First use fills a small batch quickly; background supervisor completes the universe.
    if len(rows)<20:
        scan_weekly_reversal_batch(24)
        with _LOCK:rows=[_public(v) for k,v in _PERSIST.items() if k!='__meta__' and isinstance(v,dict) and v.get('_schema')==SCHEMA_VERSION and v.get('status')=='OK']
    order={'ALIM_PENCERESİ':0,'ERKEN_DÖNÜŞ':1,'TEYİT_BEKLE':2,'NÖTR':3,'SATIŞ_RİSKİ':4}
    rows.sort(key=lambda x:(order.get(x.get('signal'),9),-x.get('score',0),-x.get('rs4',0)))
    cap=max(20,min(int(limit),120));sell_quota=max(5,min(12,cap//5))
    sell_rows=sorted([x for x in rows if x.get('signal')=='SATIŞ_RİSKİ'],key=lambda x:(x.get('score',100),x.get('rsi',100)))[:sell_quota]
    pos_rows=[x for x in rows if x.get('signal')!='SATIŞ_RİSKİ'][:max(1,cap-len(sell_rows))]
    top=pos_rows+sell_rows
    validated=[]
    def hist_one(x):
        if x.get('signal') not in {'ALIM_PENCERESİ','ERKEN_DÖNÜŞ','TEYİT_BEKLE'}: return x
        try:
            full=weekly_reversal(x['ticker'],with_history=True);h=(full.get('historical') or {})
            core=(h.get('8w') or {});trend8=((h.get('trend_confirmed') or {}).get('8w') or {})
            h8=trend8 if int(trend8.get('n') or 0)>=3 else core
            n=int(h8.get('n') or 0);hit=float(h8.get('positive_pct') or 0);med=float(h8.get('median_pct') or 0)
            x=dict(x);x['historical']=h;x['validation_basis']='TREND_CONFIRMED_8W' if h8 is trend8 else 'CORE_8W'
            reliability=min(1.0,n/8.0);edge=(hit-50)*.45+med*1.5
            x['validated_score']=round(max(0,min(100,x.get('score',0)+edge*reliability)));x['history_reliability']=round(reliability*100);return x
        except Exception:return x
    with ThreadPoolExecutor(max_workers=4) as ex:
        for x in ex.map(hist_one,top):validated.append(x)
    positives=[x for x in validated if x.get('signal')!='SATIŞ_RİSKİ']
    sells=[x for x in validated if x.get('signal')=='SATIŞ_RİSKİ']
    positives.sort(key=lambda x:(order.get(x.get('signal'),9),-x.get('validated_score',x.get('score',0)),-x.get('score',0)))
    sells.sort(key=lambda x:(x.get('score',100),x.get('rsi',100)))
    validated=positives+sells
    return {'rows':validated,'scanned':len(rows),'universe':len(u),'coverage_pct':round(len(rows)/max(1,len(u))*100,1),
            'note':'5-year weekly bars. Results come from a persistent background full-universe scan; strongest candidates get ticker-specific historical validation.'}
