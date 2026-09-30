from __future__ import annotations
import math, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
from .market_data import yahoo_rows, scan_codes
from .universe import get_universe

_LOCK=threading.Lock();_CACHE={};TTL=10*60

def _cap(x,a=0,b=100):return max(a,min(b,float(x)))
def _v(x,d=0.0):
    try:
        z=float(x);return d if math.isnan(z) or math.isinf(z) else z
    except Exception:return d

def _frame(ticker,period='5y'):
    rows=(yahoo_rows(ticker,period=period,interval='1d').get('candles') or [])
    if not rows:return None
    df=pd.DataFrame(rows).rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
    for c in ['Open','High','Low','Close','Volume']:df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df.dropna(subset=['Close']).reset_index(drop=True)
    if len(df)<80:return None
    c=df.Close;h=df.High;l=df.Low;v=df.Volume.fillna(0)
    rng=(h-l).replace(0,np.nan)
    df['CLV']=((c-l)-(h-c))/rng
    df['UPPER_WICK']=(h-np.maximum(df.Open,c))/rng
    df['LOWER_WICK']=(np.minimum(df.Open,c)-l)/rng
    mfv=df['CLV']*v
    df['CMF20']=mfv.rolling(20).sum()/v.rolling(20).sum().replace(0,np.nan)
    signed=np.sign(c.diff()).fillna(0);df['OBV']=(signed*v).cumsum()
    av=v.rolling(20).mean().replace(0,np.nan);df['VOL_RATIO']=v/av
    df['OBV_SLOPE20']=(df.OBV-df.OBV.shift(20))/(av*20)
    ret=c.pct_change();df['RET1']=ret;df['RET5']=c.pct_change(5);df['RET20']=c.pct_change(20)
    tr=pd.concat([(h-l).abs(),(h-c.shift(1)).abs(),(l-c.shift(1)).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False).mean();df['ATR_PCT']=atr/c.replace(0,np.nan)*100
    mid=c.rolling(20).mean();std=c.rolling(20).std();df['BB_WIDTH']=(4*std/mid.replace(0,np.nan))*100
    roll=df['BB_WIDTH'].rolling(120,min_periods=30)
    df['BB_PCTL']=roll.apply(lambda x: float((x<=x.iloc[-1]).mean()*100),raw=False)
    df['HI20']=c.shift(1).rolling(20).max();df['HI60']=c.shift(1).rolling(60).max()
    df['DIST_HI20']=(c/df.HI20-1)*100
    df['PRICE_PROGRESS5']=df.RET5.abs()*100
    upv=pd.Series(np.where(ret>0,v,0.0));dnv=pd.Series(np.where(ret<0,v,0.0))
    df['UP_DOWN_VOL']=upv.rolling(10).sum()/dnv.rolling(10).sum().replace(0,np.nan)
    df['POS_CLV_RATE']=(df.CLV>0).rolling(10).mean()*100
    df['UPPER_WICK5']=df.UPPER_WICK.rolling(5).mean()*100
    df['LOWER_WICK5']=df.LOWER_WICK.rolling(5).mean()*100
    df['VOL_ACCEL']=v.rolling(5).mean()/v.rolling(20).mean().replace(0,np.nan)
    # high volume with limited price travel can indicate absorption / transfer
    df['ABSORPTION']=df.VOL_RATIO/(1+df.PRICE_PROGRESS5.clip(lower=0))
    return df

def _scores(r,rs20=0.0):
    vr=_v(r.get('VOL_RATIO'),1);cmf=_v(r.get('CMF20'));obv=_v(r.get('OBV_SLOPE20'));bbp=_v(r.get('BB_PCTL'),50)
    dist=_v(r.get('DIST_HI20'),-20);ud=_v(r.get('UP_DOWN_VOL'),1);clv=_v(r.get('CLV'));pos=_v(r.get('POS_CLV_RATE'),50)
    uw=_v(r.get('UPPER_WICK5'));lw=_v(r.get('LOWER_WICK5'));va=_v(r.get('VOL_ACCEL'),1);ret5=_v(r.get('RET5'))*100;ret20=_v(r.get('RET20'))*100
    absorption=_v(r.get('ABSORPTION'),0)
    acc=45
    acc+=12 if cmf>.10 else 6 if cmf>0 else -10 if cmf<-.10 else 0
    acc+=10 if obv>.04 else 5 if obv>0 else -8
    acc+=10 if ud>1.35 else 5 if ud>1.05 else -6 if ud<.75 else 0
    acc+=8 if pos>=65 else 4 if pos>=55 else -5 if pos<40 else 0
    acc+=8 if bbp<=25 else 3 if bbp<=40 else 0
    acc+=6 if va>=1.15 and ret5<8 else 0
    acc+=5 if absorption>.35 else 0
    acc+=max(-6,min(8,rs20*.35))
    acc-=8 if ret20>25 else 0
    acc=_cap(acc)

    markup=38+.38*acc
    markup+=10 if -3<=dist<=1 else 4 if -8<=dist<-3 else 0
    markup+=8 if vr>=1.4 else 4 if vr>=1.1 else 0
    markup+=7 if ret5>0 else -5 if ret5<-4 else 0
    markup+=max(-8,min(10,rs20*.45))
    markup-=6 if bbp>75 and ret20>15 else 0
    markup=_cap(markup)

    dist_score=35
    if ret20>12:dist_score+=10
    if vr>1.5 and abs(ret5)<4:dist_score+=12
    if uw>=32:dist_score+=12
    if cmf<0:dist_score+=12
    if obv<0:dist_score+=10
    if ud<.8:dist_score+=8
    if clv<-.25:dist_score+=7
    if dist>=-3:dist_score+=6
    dist_score=_cap(dist_score)

    exit_risk=.72*dist_score+.28*(100-acc)
    if ret5<-5 and vr>1.2:exit_risk+=8
    exit_risk=_cap(exit_risk)
    return round(acc),round(markup),round(dist_score),round(exit_risk)

def smart_money_snapshot(ticker,calibrate=True):
    code=ticker.upper().replace('.IS','');key=f'sm:{code}:{int(bool(calibrate))}';now=time.time()
    with _LOCK:
        hit=_CACHE.get(key)
        if hit and now-hit[0]<TTL:return hit[1]
    df=_frame(code,'5y')
    if df is None:return {'ticker':code,'status':'NO_DATA'}
    bench=_frame('XU100','5y')
    rs20=0
    if bench is not None and len(bench)>=21 and len(df)>=21:
        rs20=((df.Close.iloc[-1]/df.Close.iloc[-21]-1)-(bench.Close.iloc[-1]/bench.Close.iloc[-21]-1))*100
    r=df.iloc[-1]
    acc,markup,distribution,exit_risk=_scores(r,rs20)
    phase='PRE_MARKUP_WATCH' if acc>=72 and markup>=68 and distribution<65 else 'MARKUP' if markup>=78 and _v(r.RET5)>0 else 'DISTRIBUTION_RISK' if distribution>=72 else 'NEUTRAL'
    reasons=[]
    if _v(r.CMF20)>.1:reasons.append('CMF pozitif para akışı')
    if _v(r.OBV_SLOPE20)>.04:reasons.append('OBV yükseliyor')
    if _v(r.BB_PCTL,50)<=25:reasons.append('volatilite sıkışması')
    if _v(r.UP_DOWN_VOL,1)>1.35:reasons.append('yukarı gün hacmi baskın')
    if -3<=_v(r.DIST_HI20,-20)<=1:reasons.append('20G zirve eşiğinde')
    if _v(r.UPPER_WICK5)>32:reasons.append('üst fitil yoğunluğu')
    if _v(r.VOL_RATIO,1)>1.5 and abs(_v(r.RET5)*100)<4:reasons.append('yüksek hacim / düşük fiyat ilerlemesi')
    hist=None
    if calibrate:
        vals=[];step=3
        for i in range(70,len(df)-11,step):
            row=df.iloc[i]
            a,m,d,e=_scores(row,0)
            p=float(df.Close.iloc[i]);f10=float(df.Close.iloc[i+10]);mx=float(df.Close.iloc[i+1:i+11].max());mn=float(df.Close.iloc[i+1:i+11].min())
            vals.append({'a':a,'m':m,'d':d,'e':e,'f10':(f10/p-1)*100,'max10':(mx/p-1)*100,'min10':(mn/p-1)*100})
        pre=[x for x in vals if x['a']>=72 and x['m']>=68 and x['d']<65]
        ds=[x for x in vals if x['d']>=72]
        def smp(xs,kind):
            if not xs:return {'n':0}
            if kind=='markup':
                hit=sum(1 for x in xs if x['max10']>=12)/len(xs)*100;med=float(np.median([x['f10'] for x in xs]))
                return {'n':len(xs),'hit_rate_pct':round(hit,1),'median_forward10_pct':round(med,2),'definition':'forward 10 sessions max gain >=12%'}
            hit=sum(1 for x in xs if x['min10']<=-8)/len(xs)*100;med=float(np.median([x['f10'] for x in xs]))
            return {'n':len(xs),'hit_rate_pct':round(hit,1),'median_forward10_pct':round(med,2),'definition':'forward 10 sessions min return <=-8%'}
        hist={'pre_markup':smp(pre,'markup'),'distribution':smp(ds,'distribution'),'sample_step':step,
              'note':'Ticker-specific historical calibration from past OHLCV only; thresholds are heuristic and do not identify a specific actor.'}
    out={'ticker':code,'status':'OK','phase':phase,'accumulation_probability':acc,'markup_probability':markup,'distribution_risk':distribution,'exit_risk':exit_risk,
         'features':{'cmf20':round(_v(r.CMF20),3),'obv_slope20':round(_v(r.OBV_SLOPE20),3),'volume_ratio':round(_v(r.VOL_RATIO,1),2),
          'up_down_volume_ratio':round(_v(r.UP_DOWN_VOL,1),2),'bb_width_percentile':round(_v(r.BB_PCTL,50),1),'distance_to_20d_high_pct':round(_v(r.DIST_HI20),2),
          'upper_wick_5d_pct':round(_v(r.UPPER_WICK5),1),'lower_wick_5d_pct':round(_v(r.LOWER_WICK5),1),'positive_clv_rate_pct':round(_v(r.POS_CLV_RATE),1),
          'volume_acceleration':round(_v(r.VOL_ACCEL,1),2),'rs20_vs_xu100_pct':round(rs20,2)},
         'reasons':reasons[:8],'historical_calibration':hist,
         'warning':'These are market-behaviour probabilities from OHLCV proxies. They do not prove that a manipulator, market maker, broker or specific person is entering or exiting.'}
    with _LOCK:_CACHE[key]=(now,out)
    return out

def smart_money_radar(limit=25,universe_limit=0):
    # Prefer the candidate set already produced by the full-universe background radar.
    try:
        from .opportunity_engine import smart_money_candidates as _candidate_snapshot
        cached=(_candidate_snapshot(limit=60).get('rows') or [])
    except Exception:
        cached=[]
    if cached:
        pre=cached[:50]; scan_count=-1
    else:
        universe=get_universe()
        cap=len(universe) if int(universe_limit or 0)<=0 else max(40,min(int(universe_limit),len(universe)))
        codes=[x['ticker'] for x in universe[:cap]]
        scan=scan_codes(codes);scan_count=len(scan)
        pre=sorted(scan,key=lambda x:(x.get('smart_money_score',0),x.get('relative_strength_20',0)),reverse=True)[:50]
    rows=[]
    def one(code):
        return smart_money_snapshot(code,calibrate=False)
    with ThreadPoolExecutor(max_workers=6) as ex:
        fut=[ex.submit(one,x['ticker']) for x in pre]
        for q in as_completed(fut):
            try:
                s=q.result()
                if s.get('status')=='OK':rows.append(s)
            except Exception:pass
    rows.sort(key=lambda x:(max(x['accumulation_probability'],x['distribution_risk']),x['markup_probability']),reverse=True)
    return {'rows':rows[:max(5,min(int(limit),50))],'scanned':scan_count,'deep_analyzed':len(rows),
            'source':'FULL_UNIVERSE_BACKGROUND_CANDIDATES' if cached else 'ON_DEMAND_SCAN',
            'note':'Radar deep-analyzes the strongest price/volume candidates. When the background radar has run, candidates originate from its full-universe scan.'}
