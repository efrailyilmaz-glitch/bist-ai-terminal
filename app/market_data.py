from __future__ import annotations
import time, threading, requests
import pandas as pd
import yfinance as yf
from .scoring import score_frame

_LOCK=threading.Lock(); _SCAN_CACHE={}; _CHART_CACHE={}

def _norm(df):
    if df is None or df.empty: return pd.DataFrame()
    out=df.copy()
    if isinstance(out.columns,pd.MultiIndex):
        if len(set(out.columns.get_level_values(0)))==1: out.columns=out.columns.get_level_values(1)
        elif len(set(out.columns.get_level_values(1)))==1: out.columns=out.columns.get_level_values(0)
    return out

def scan_codes(codes):
    codes=[c.upper().replace('.IS','') for c in codes if c]
    key=','.join(codes); now=time.time()
    with _LOCK:
        hit=_SCAN_CACHE.get(key)
        if hit and now-hit[0] < 600: return hit[1]
    syms=[c+'.IS' for c in codes]
    results=[]
    try:
        raw=yf.download(syms,period='1y',interval='1d',group_by='ticker',auto_adjust=True,threads=True,progress=False,timeout=20)
        for code,sym in zip(codes,syms):
            try:
                df=_norm(raw[sym] if isinstance(raw.columns,pd.MultiIndex) and sym in raw.columns.get_level_values(0) else raw)
                sc=score_frame(df)
                if sc: results.append({'ticker':code,**sc})
            except Exception: continue
    except Exception: pass
    with _LOCK: _SCAN_CACHE[key]=(now,results)
    return results

def yahoo_chart(code, period='1y', interval='1d'):
    code=code.upper().replace('.IS','')
    period=period if period in {'1mo','3mo','6mo','1y','2y','5y'} else '1y'
    interval=interval if interval in {'15m','30m','60m','1d','1wk'} else '1d'
    if interval in {'15m','30m'} and period not in {'1mo'}: period='1mo'
    if interval=='60m' and period in {'1y','2y','5y'}: period='6mo'
    key=f'{code}:{period}:{interval}'; now=time.time()
    with _LOCK:
        hit=_CHART_CACHE.get(key)
        if hit and now-hit[0] < 180: return hit[1]
    symbol=code if code.startswith('^') or '=' in code or '.' in code or '-' in code else code+'.IS'
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
    r=requests.get(url,params={'range':period,'interval':interval,'includePrePost':'false','events':'div,splits'},headers={'User-Agent':'Mozilla/5.0'},timeout=20)
    r.raise_for_status()
    result=r.json().get('chart',{}).get('result') or []
    if not result: raise ValueError('Yahoo returned no chart result')
    obj=result[0]; ts=obj.get('timestamp') or []; q=obj['indicators']['quote'][0]
    rows=[]
    for i,t in enumerate(ts):
        try:
            o,h,l,c,v=q['open'][i],q['high'][i],q['low'][i],q['close'][i],q['volume'][i]
            if None in (o,h,l,c): continue
            tm=int(t) if interval not in {'1d','1wk'} else time.strftime('%Y-%m-%d',time.gmtime(t))
            rows.append({'time':tm,'open':round(float(o),4),'high':round(float(h),4),'low':round(float(l),4),'close':round(float(c),4),'volume':int(v or 0)})
        except Exception: continue
    df=pd.DataFrame(rows)
    if not df.empty:
        close=df['close']
        for n in (20,50,200): df[f'ma{n}']=close.rolling(n).mean()
    data={'ticker':code,'period':period,'interval':interval,'currency':(obj.get('meta') or {}).get('currency','TRY'),'candles':rows,
          'ma20':[{'time':r['time'],'value':round(float(m),4)} for r,m in zip(rows,df.get('ma20',[])) if pd.notna(m)],
          'ma50':[{'time':r['time'],'value':round(float(m),4)} for r,m in zip(rows,df.get('ma50',[])) if pd.notna(m)],
          'ma200':[{'time':r['time'],'value':round(float(m),4)} for r,m in zip(rows,df.get('ma200',[])) if pd.notna(m)]}
    with _LOCK: _CHART_CACHE[key]=(now,data)
    return data

def market_overview():
    out={'mode':'LIVE / YAHOO','updated':time.strftime('%d.%m.%Y %H:%M:%S'),'global_score':50,'regime':'NÖTR','fear':50,'breadth':0,'advancers':0,'decliners':0,'unchanged':0}
    symbols=[('xu100','XU100'),('usdtry','TRY=X'),('eurtry','EURTRY=X'),('sp500','^GSPC'),('nasdaq','^IXIC'),('dxy','DX-Y.NYB'),('us10y','^TNX'),('gold','GC=F'),('oil','CL=F')]
    ok=0
    for key,sym in symbols:
        try:
            d=yahoo_chart(sym,period='1mo',interval='1d')
            if d and len(d['candles'])>=2:
                a,b=d['candles'][-1]['close'],d['candles'][-2]['close']
                out[key]=a; out[key+'_change']=round((a/b-1)*100,2); ok+=1
            else: out[key]=0; out[key+'_change']=0
        except Exception:
            out[key]=0; out[key+'_change']=0
    score=50
    score += 12 if out.get('sp500_change',0)>0 else -10
    score += 10 if out.get('nasdaq_change',0)>0 else -8
    score += 14 if out.get('xu100_change',0)>0 else -12
    score += -8 if out.get('usdtry_change',0)>0.35 else (4 if out.get('usdtry_change',0)<0 else 0)
    score += -5 if out.get('us10y_change',0)>1 else 2
    score += -4 if out.get('dxy_change',0)>0.5 else 2
    score=int(max(0,min(100,score))); out['global_score']=score
    out['regime']='RISK-ON / BULL' if score>=62 else ('RISK-OFF / BEAR' if score<=38 else 'NÖTR / TRANSITION')
    out['mode']='LIVE / YAHOO' if ok>=3 else ('PARTIAL / YAHOO' if ok else 'DATA UNAVAILABLE')
    return out
