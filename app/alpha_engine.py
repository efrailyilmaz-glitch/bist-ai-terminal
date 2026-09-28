from __future__ import annotations
import math, re, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List
import numpy as np
import pandas as pd
from .market_data import yahoo_rows, scan_codes
from .scoring import score_frame
from .fundamentals import get_fundamentals
from .universe import get_universe
from .kap_engine import disclosures

_LOCK=threading.Lock();_CACHE={};TTL=30*60

def _df(ticker,period='10y'):
    d=yahoo_rows(ticker,period=period,interval='1d');rows=d.get('candles') or []
    if len(rows)<260:return None,rows
    x=pd.DataFrame(rows).rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
    return x,rows

def _regime(bench:pd.DataFrame,idx:int):
    if idx<200:return 'UNKNOWN'
    c=bench['Close'].astype(float).iloc[:idx+1]
    e50=c.ewm(span=50,adjust=False).mean().iloc[-1];e200=c.ewm(span=200,adjust=False).mean().iloc[-1]
    vol=c.pct_change().tail(20).std()*math.sqrt(252)*100
    if c.iloc[-1]>e50>e200:return 'BULL'
    if c.iloc[-1]<e50<e200:return 'BEAR'
    return 'HIGH_VOL_SIDEWAYS' if vol>35 else 'SIDEWAYS'

def _ci95(values):
    a=np.asarray([x for x in values if x is not None and np.isfinite(x)],float)
    if len(a)<2:return None
    m=float(a.mean());se=float(a.std(ddof=1)/math.sqrt(len(a)))
    return [round(m-1.96*se,2),round(m+1.96*se,2)]

def _summ(events,h):
    vals=[e[f'excess_{h}'] for e in events if e.get(f'excess_{h}') is not None]
    raw=[e[f'return_{h}'] for e in events if e.get(f'return_{h}') is not None]
    if not vals:return {'n':0}
    arr=np.array(vals,float)
    return {'n':len(arr),'hit_rate_pct':round(float((arr>0).mean()*100),1),'median_excess_pct':round(float(np.median(arr)),2),
            'mean_excess_pct':round(float(arr.mean()),2),'mean_return_pct':round(float(np.mean(raw)),2) if raw else None,
            'ci95_mean_excess_pct':_ci95(vals),'p10_excess_pct':round(float(np.quantile(arr,.10)),2),'p90_excess_pct':round(float(np.quantile(arr,.90)),2)}

def validate_alpha(ticker:str,period='10y',step=5,min_score=60):
    code=ticker.upper().replace('.IS','');key=f'alpha:{code}:{period}:{step}:{min_score}';now=time.time()
    with _LOCK:
        h=_CACHE.get(key)
        if h and now-h[0]<TTL:return h[1]
    df,rows=_df(code,period);bench,brows=_df('XU100',period)
    if df is None or bench is None:return {'ticker':code,'status':'NO_DATA'}
    n=min(len(df),len(bench));df=df.iloc[-n:].reset_index(drop=True);bench=bench.iloc[-n:].reset_index(drop=True);rows=rows[-n:];events=[]
    for i in range(220,n-61,max(1,int(step))):
        hist=df.iloc[:i+1];bh=bench.iloc[:i+1]
        b20=(bh['Close'].iloc[-1]/bh['Close'].iloc[-21]-1)*100 if len(bh)>=21 else 0
        b60=(bh['Close'].iloc[-1]/bh['Close'].iloc[-61]-1)*100 if len(bh)>=61 else b20
        s=score_frame(hist,b20,b60)
        if not s:continue
        score=round(.55*s['short_score']+.45*s['long_score'])
        if score<int(min_score):continue
        e={'time':rows[i]['time'],'score':score,'short_score':s['short_score'],'long_score':s['long_score'],'regime':_regime(bench,i)}
        for hzn in (5,20,60):
            if i+hzn<n:
                r=(df['Close'].iloc[i+hzn]/df['Close'].iloc[i]-1)*100
                br=(bench['Close'].iloc[i+hzn]/bench['Close'].iloc[i]-1)*100
                e[f'return_{hzn}']=round(float(r),2);e[f'excess_{hzn}']=round(float(r-br),2)
        events.append(e)
    buckets={}
    for lo,hi,label in [(60,69,'60–69'),(70,79,'70–79'),(80,89,'80–89'),(90,100,'90–100')]:
        ev=[x for x in events if lo<=x['score']<=hi]
        buckets[label]={'n':len(ev),'h20':_summ(ev,20),'h60':_summ(ev,60)}
    regimes={}
    for rg in ['BULL','SIDEWAYS','HIGH_VOL_SIDEWAYS','BEAR']:
        ev=[x for x in events if x['regime']==rg]
        regimes[rg]={'n':len(ev),'h5':_summ(ev,5),'h20':_summ(ev,20),'h60':_summ(ev,60)}
    out={'ticker':code,'status':'OK','period':period,'sample_count':len(events),'min_score':min_score,
         'horizons':{'5d':_summ(events,5),'20d':_summ(events,20),'60d':_summ(events,60)},'calibration':buckets,'regimes':regimes,
         'recent_events':events[-30:][::-1],
         'note':'Historical point-in-time technical score validation using only data available up to each sample date. Current-universe survivorship bias remains.'}
    with _LOCK:_CACHE[key]=(now,out)
    return out

def ensemble_signal(ticker:str):
    code=ticker.upper().replace('.IS','');rows=scan_codes([code]);t=rows[0] if rows else {}
    if not t:return {'ticker':code,'status':'NO_DATA'}
    trend=max(0,min(100,50+(18 if t.get('above_ema200') else -18)+(10 if t.get('supertrend')=='BULLISH' else -10)+(10 if t.get('ichimoku')=='BULLISH' else -10)))
    momentum=max(0,min(100,50+t.get('momentum_20',0)*.6+t.get('momentum_60',0)*.25+t.get('relative_strength_20',0)*.45))
    breakout=max(0,min(100,45+(20 if t.get('breakout20') else 0)+max(-10,min(20,(t.get('volume_ratio',1)-1)*15))))
    meanrev=max(0,min(100,50+(30-t.get('rsi',50))*.8 if t.get('rsi',50)<40 else 50-(t.get('rsi',50)-70)*.8 if t.get('rsi',50)>70 else 50))
    quality=max(0,min(100,100-t.get('risk',50)*.45-t.get('anomaly_score',0)*.25+25))
    scores={'trend':round(trend),'momentum':round(momentum),'breakout':round(breakout),'mean_reversion':round(meanrev),'risk_quality':round(quality)}
    weights={'trend':.28,'momentum':.27,'breakout':.18,'mean_reversion':.10,'risk_quality':.17}
    total=round(sum(scores[k]*weights[k] for k in weights))
    dispersion=round(float(np.std(list(scores.values()))),1)
    return {'ticker':code,'status':'OK','ensemble_score':total,'dispersion':dispersion,'agreement':'HIGH' if dispersion<12 else 'MEDIUM' if dispersion<22 else 'LOW','models':scores,'weights':weights}

def sector_rotation(limit=40):
    key=f'sectors:{limit}';now=time.time()
    with _LOCK:
        h=_CACHE.get(key)
        if h and now-h[0]<TTL:return h[1]
    universe=get_universe();codes=[x['ticker'] for x in universe]
    scanned=scan_codes(codes)
    scanned=sorted(scanned,key=lambda x:x.get('avg_value_turnover_20',0),reverse=True)[:max(20,min(int(limit),60))]
    sectors={}
    with ThreadPoolExecutor(max_workers=6) as ex:
        fut={ex.submit(get_fundamentals,r['ticker']):r for r in scanned}
        for q in as_completed(fut):
            r=fut[q]
            try:f=q.result()
            except Exception:continue
            sec=f.get('sector') or 'Unknown'
            sectors.setdefault(sec,[]).append(r)
    rows=[]
    for sec,grp in sectors.items():
        if len(grp)<2:continue
        rs20=np.mean([x.get('relative_strength_20',0) for x in grp]);rs60=np.mean([x.get('relative_strength_60',0) for x in grp]);mom=np.mean([x.get('momentum_20',0) for x in grp]);breadth=np.mean([1 if x.get('above_ema50') else 0 for x in grp])*100
        score=round(max(0,min(100,50+rs20*.8+rs60*.35+mom*.35+(breadth-50)*.25)))
        rows.append({'sector':sec,'score':score,'sample_size':len(grp),'rs20':round(float(rs20),1),'rs60':round(float(rs60),1),'momentum20':round(float(mom),1),'breadth_ema50_pct':round(float(breadth),1)})
    rows.sort(key=lambda x:x['score'],reverse=True)
    out={'status':'OK','rows':rows,'sample_count':len(scanned),'scope':'Most liquid available sample; not full-sector constituent history.'}
    with _LOCK:_CACHE[key]=(now,out)
    return out

def event_study(ticker:str,limit=20):
    code=ticker.upper().replace('.IS','');d=disclosures(code,limit=limit);items=d.get('items') or []
    df,rows=_df(code,'5y');bench,brows=_df('XU100','5y')
    if df is None or bench is None:return {'ticker':code,'status':'NO_PRICE_DATA','events':[]}
    dates=[str(x['time'])[:10] for x in rows];bdates=[str(x['time'])[:10] for x in brows];bmap={d:i for i,d in enumerate(bdates)};events=[]
    for it in items:
        ds=it.get('date')
        if not ds:continue
        try:
            p=ds.split('.');iso=f'{p[2]}-{p[1].zfill(2)}-{p[0].zfill(2)}' if len(p)==3 else ds
        except Exception:continue
        idx=next((i for i,x in enumerate(dates) if x>=iso),None);bi=next((i for i,x in enumerate(bdates) if x>=iso),None)
        if idx is None or bi is None:continue
        ev={'date':ds,'category':it.get('event_category'),'title':it.get('title'),'materiality':it.get('materiality'),'sentiment_score':it.get('sentiment_score')}
        for h in (1,5,20):
            if idx+h<len(df) and bi+h<len(bench):
                r=(df['Close'].iloc[idx+h]/df['Close'].iloc[idx]-1)*100;br=(bench['Close'].iloc[bi+h]/bench['Close'].iloc[bi]-1)*100
                ev[f'return_{h}d']=round(float(r),2);ev[f'excess_{h}d']=round(float(r-br),2)
        events.append(ev)
    summary={}
    cats=sorted(set(x.get('category') for x in events if x.get('category')))
    for cat in cats:
        ev=[x for x in events if x.get('category')==cat]
        vals=[x.get('excess_20d') for x in ev if x.get('excess_20d') is not None]
        summary[cat]={'n':len(ev),'mean_excess_20d':round(float(np.mean(vals)),2) if vals else None,'hit_rate_20d':round(float(np.mean(np.array(vals)>0)*100),1) if vals else None}
    return {'ticker':code,'status':'OK' if events else 'NO_DATED_EVENTS','events':events,'summary':summary,'note':'Public KAP search event dates matched to next available trading day; small samples are not statistically reliable.'}
