from __future__ import annotations
import math, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
from .market_data import yahoo_rows, scan_codes, market_overview
from .universe import get_universe

_LOCK=threading.Lock();_CACHE={};TTL=15*60

def _v(x,d=None):
    try:
        if x is None:return d
        z=float(x);return d if math.isnan(z) or math.isinf(z) else z
    except Exception:return d

def _returns(ticker,period='10y'):
    d=yahoo_rows(ticker,period=period,interval='1d');rows=d.get('candles') or []
    if not rows:return None
    df=pd.DataFrame(rows)
    df['date']=pd.to_datetime(df['time'],errors='coerce')
    df=df.dropna(subset=['date']).sort_values('date').set_index('date')
    df['close']=df['close'].astype(float)
    df['ret']=df['close'].pct_change()
    return df

def seasonality(ticker,period='10y'):
    code=ticker.upper().replace('.IS','');key=f'season:{code}:{period}';now=time.time()
    with _LOCK:
        h=_CACHE.get(key)
        if h and now-h[0]<TTL:return h[1]
    df=_returns(code,period)
    if df is None or len(df)<260:return {'ticker':code,'status':'NO_DATA'}
    mclose=df['close'].resample('ME').last().dropna()
    mret=mclose.pct_change().dropna()*100
    months=[]
    names=['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara']
    for m in range(1,13):
        vals=mret[mret.index.month==m].values
        months.append({'month':m,'name':names[m-1],'n':len(vals),'mean_pct':round(float(np.mean(vals)),2) if len(vals) else None,
                       'median_pct':round(float(np.median(vals)),2) if len(vals) else None,'positive_pct':round(float((vals>0).mean()*100),1) if len(vals) else None,
                       'best_pct':round(float(np.max(vals)),2) if len(vals) else None,'worst_pct':round(float(np.min(vals)),2) if len(vals) else None})
    daily=(df['ret'].dropna()*100)
    weekdays=[]
    wnames=['Pzt','Sal','Çar','Per','Cum']
    for w in range(5):
        vals=daily[daily.index.weekday==w].values
        weekdays.append({'weekday':w,'name':wnames[w],'n':len(vals),'mean_pct':round(float(np.mean(vals)),3) if len(vals) else None,
                         'median_pct':round(float(np.median(vals)),3) if len(vals) else None,'positive_pct':round(float((vals>0).mean()*100),1) if len(vals) else None})
    q={}
    for quarter in range(1,5):
        vals=mret[mret.index.quarter==quarter].values
        q[f'Q{quarter}']={'n':len(vals),'mean_pct':round(float(np.mean(vals)),2) if len(vals) else None,'positive_pct':round(float((vals>0).mean()*100),1) if len(vals) else None}
    out={'ticker':code,'status':'OK','period':period,'months':months,'weekdays':weekdays,'quarters':q,
         'note':'Calendar seasonality is descriptive historical evidence; structural changes can make past seasonal patterns disappear.'}
    with _LOCK:_CACHE[key]=(now,out)
    return out

def _align_pair(ticker,period='5y'):
    a=_returns(ticker,period);b=_returns('XU100',period)
    if a is None or b is None:return None
    x=pd.DataFrame({'asset':a['ret'],'bench':b['ret']}).dropna()
    return x

def rolling_risk(ticker,period='5y'):
    code=ticker.upper().replace('.IS','');key=f'riskintel:{code}:{period}';now=time.time()
    with _LOCK:
        h=_CACHE.get(key)
        if h and now-h[0]<TTL:return h[1]
    x=_align_pair(code,period)
    df=_returns(code,period)
    if x is None or df is None or len(x)<100:return {'ticker':code,'status':'NO_DATA'}
    def beta(n,down=False):
        z=x.tail(n)
        if down:z=z[z['bench']<0]
        if len(z)<15:return None
        vb=float(z['bench'].var())
        return None if vb<=0 else round(float(z[['asset','bench']].cov().iloc[0,1]/vb),2)
    def corr(n):
        z=x.tail(n)
        return round(float(z['asset'].corr(z['bench'])),2) if len(z)>=20 else None
    r=x['asset'].dropna()
    ann_vol=float(r.std()*math.sqrt(252)*100)
    downside=r[r<0];down_dev=float(downside.std()*math.sqrt(252)*100) if len(downside)>2 else None
    var95=float(np.quantile(r,.05)*100);cvar=float(r[r<=np.quantile(r,.05)].mean()*100)
    close=df['close'].astype(float);peak=close.cummax();dd=(close/peak-1)*100
    maxdd=float(dd.min())
    up=x[x['bench']>0];dn=x[x['bench']<0]
    upcap=(up['asset'].mean()/up['bench'].mean()*100) if len(up)>10 and up['bench'].mean()!=0 else None
    downcap=(dn['asset'].mean()/dn['bench'].mean()*100) if len(dn)>10 and dn['bench'].mean()!=0 else None
    out={'ticker':code,'status':'OK','beta_60':beta(60),'beta_120':beta(120),'beta_252':beta(252),'downside_beta_252':beta(252,True),
         'corr_60':corr(60),'corr_120':corr(120),'corr_252':corr(252),'annual_volatility_pct':round(ann_vol,1),
         'downside_deviation_pct':None if down_dev is None else round(down_dev,1),'var95_daily_pct':round(var95,2),'cvar95_daily_pct':round(cvar,2),
         'max_drawdown_pct':round(maxdd,1),'up_capture_pct':None if upcap is None else round(float(upcap),1),
         'down_capture_pct':None if downcap is None else round(float(downcap),1),
         'skew':round(float(r.skew()),2),'kurtosis':round(float(r.kurt()),2),
         'note':'Beta/correlation are trailing historical estimates versus XU100 and can change quickly in a new regime.'}
    with _LOCK:_CACHE[key]=(now,out)
    return out

def relative_rotation(codes):
    codes=list(dict.fromkeys([x.upper().replace('.IS','') for x in codes if x]))[:20]
    bench=_returns('XU100','2y')
    if bench is None:return {'status':'NO_BENCHMARK','rows':[]}
    data=[]
    def one(code):
        a=_returns(code,'2y')
        if a is None:return None
        z=pd.DataFrame({'a':a['close'],'b':bench['close']}).dropna()
        if len(z)<80:return None
        rel=np.log(z['a']/z['b'])
        rs20=(rel.iloc[-1]-rel.iloc[-21])*100
        rs60=(rel.iloc[-1]-rel.iloc[-61])*100
        mom=rs20-rs60/3
        return {'ticker':code,'rs20_raw':float(rs20),'rs60_raw':float(rs60),'momentum_raw':float(mom)}
    with ThreadPoolExecutor(max_workers=6) as ex:
        fut=[ex.submit(one,c) for c in codes]
        for q in as_completed(fut):
            try:
                r=q.result()
                if r:data.append(r)
            except Exception:pass
    if not data:return {'status':'NO_DATA','rows':[]}
    rs=np.array([x['rs60_raw'] for x in data],float);mo=np.array([x['momentum_raw'] for x in data],float)
    rstd=rs.std() or 1;mstd=mo.std() or 1
    for i,x in enumerate(data):
        ratio=100+(rs[i]-rs.mean())/rstd*10
        momentum=100+(mo[i]-mo.mean())/mstd*10
        if ratio>=100 and momentum>=100:q='LEADING'
        elif ratio>=100 and momentum<100:q='WEAKENING'
        elif ratio<100 and momentum<100:q='LAGGING'
        else:q='IMPROVING'
        x.update({'rs_ratio':round(float(ratio),1),'rs_momentum':round(float(momentum),1),'quadrant':q})
    data.sort(key=lambda x:(x['quadrant']!='LEADING',-x['rs_ratio'],-x['rs_momentum']))
    return {'status':'OK','rows':data,'note':'RRG-style cross-sectional normalization versus XU100; not an official JdK RRG implementation.'}

def watchlist_heatmap(codes):
    codes=list(dict.fromkeys([x.upper().replace('.IS','') for x in codes if x]))[:25]
    rows=scan_codes(codes)
    out=[]
    for x in rows:
        out.append({'ticker':x.get('ticker'),'price':x.get('price'),'change':x.get('change'),'short_score':x.get('short_score'),'long_score':x.get('long_score'),
                    'alpha_score':x.get('alpha_score'),'risk':x.get('risk'),'anomaly_score':x.get('anomaly_score'),'rs20':x.get('relative_strength_20'),
                    'rs60':x.get('relative_strength_60'),'volume_ratio':x.get('volume_ratio'),'rsi':x.get('rsi'),'supertrend':x.get('supertrend'),'ichimoku':x.get('ichimoku')})
    return {'rows':out}

def market_regime_dashboard():
    key='regime-dashboard';now=time.time()
    with _LOCK:
        h=_CACHE.get(key)
        if h and now-h[0]<TTL:return h[1]
    idx=_returns('XU100','2y')
    if idx is None or len(idx)<220:return {'status':'NO_DATA'}
    c=idx['close'];e20=c.ewm(span=20,adjust=False).mean();e50=c.ewm(span=50,adjust=False).mean();e200=c.ewm(span=200,adjust=False).mean()
    vol20=idx['ret'].tail(20).std()*math.sqrt(252)*100;vol60=idx['ret'].tail(60).std()*math.sqrt(252)*100
    mom20=(c.iloc[-1]/c.iloc[-21]-1)*100;mom60=(c.iloc[-1]/c.iloc[-61]-1)*100
    if c.iloc[-1]>e20.iloc[-1]>e50.iloc[-1]>e200.iloc[-1] and mom20>0:regime='BULL_TREND'
    elif c.iloc[-1]<e20.iloc[-1]<e50.iloc[-1] and mom20<0:regime='BEAR_TREND'
    elif vol20>max(35,vol60*1.25):regime='HIGH_VOLATILITY'
    else:regime='RANGE'
    sample=[x['ticker'] for x in get_universe()[:100]]
    scan=scan_codes(sample)
    breadth20=np.mean([1 if x.get('above_ema20') else 0 for x in scan])*100 if scan else None
    breadth50=np.mean([1 if x.get('above_ema50') else 0 for x in scan])*100 if scan else None
    breadth200=np.mean([1 if x.get('above_ema200') else 0 for x in scan])*100 if scan else None
    score=50
    score+=20 if regime=='BULL_TREND' else -20 if regime=='BEAR_TREND' else -8 if regime=='HIGH_VOLATILITY' else 0
    score+=((breadth50 or 50)-50)*.35
    score+=max(-10,min(10,mom20*.4))
    score-=max(0,vol20-30)*.25
    score=max(0,min(100,round(score)))
    out={'status':'OK','regime':regime,'regime_score':score,'xu100':round(float(c.iloc[-1]),2),'momentum20_pct':round(float(mom20),1),'momentum60_pct':round(float(mom60),1),
         'volatility20_pct':round(float(vol20),1),'volatility60_pct':round(float(vol60),1),'breadth_ema20_pct':None if breadth20 is None else round(float(breadth20),1),
         'breadth_ema50_pct':None if breadth50 is None else round(float(breadth50),1),'breadth_ema200_pct':None if breadth200 is None else round(float(breadth200),1),
         'macro':market_overview(),'sample_size':len(scan),'note':'Breadth uses the first available 100-symbol universe sample; full historical constituent breadth requires a dedicated licensed/history source.'}
    with _LOCK:_CACHE[key]=(now,out)
    return out
