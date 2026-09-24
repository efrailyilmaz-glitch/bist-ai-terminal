from __future__ import annotations
import time, threading, requests
import pandas as pd
import yfinance as yf
from .scoring import score_frame, indicator_frame
from .advanced_indicators import advanced_series, analyze_structure

_LOCK=threading.Lock()
_SCAN_CACHE={}
_CHART_CACHE={}

def _norm(df):
    if df is None or df.empty:
        return pd.DataFrame()
    out=df.copy()
    if isinstance(out.columns,pd.MultiIndex):
        if len(set(out.columns.get_level_values(0)))==1:
            out.columns=out.columns.get_level_values(1)
        elif len(set(out.columns.get_level_values(1)))==1:
            out.columns=out.columns.get_level_values(0)
    return out

def _extract(raw, symbol):
    if raw is None or raw.empty:
        return pd.DataFrame()
    if not isinstance(raw.columns,pd.MultiIndex):
        return _norm(raw)
    l0=list(raw.columns.get_level_values(0))
    l1=list(raw.columns.get_level_values(1))
    try:
        if symbol in l0:
            return _norm(raw[symbol])
        if symbol in l1:
            return _norm(raw.xs(symbol,axis=1,level=1))
    except Exception:
        pass
    return pd.DataFrame()

def _ret(df,n):
    try:
        c=pd.to_numeric(df['Close'],errors='coerce').dropna()
        if len(c)<=n: return 0.0
        return float((c.iloc[-1]/c.iloc[-(n+1)]-1)*100)
    except Exception:
        return 0.0

def scan_codes(codes):
    codes=[c.upper().replace('.IS','') for c in codes if c]
    key=','.join(codes)
    now=time.time()
    with _LOCK:
        hit=_SCAN_CACHE.get(key)
        if hit and now-hit[0] < 600:
            return hit[1]

    syms=[c+'.IS' for c in codes]
    download_syms=list(dict.fromkeys(syms+['XU100.IS']))
    results=[]
    try:
        raw=yf.download(download_syms,period='1y',interval='1d',group_by='ticker',auto_adjust=True,threads=True,progress=False,timeout=25)
        bench=_extract(raw,'XU100.IS')
        br20=_ret(bench,20)
        br60=_ret(bench,60)
        for code,sym in zip(codes,syms):
            try:
                df=_extract(raw,sym)
                if df.empty: continue
                sc=score_frame(df,benchmark_return_20=br20,benchmark_return_60=br60)
                if sc:
                    results.append({'ticker':code,**sc})
            except Exception:
                continue
    except Exception:
        pass

    with _LOCK:
        _SCAN_CACHE[key]=(now,results)
    return results

def _series(rows, values, digits=4):
    out=[]
    for row,val in zip(rows,values):
        if pd.notna(val):
            out.append({'time':row['time'],'value':round(float(val),digits)})
    return out

def yahoo_chart(code, period='1y', interval='1d'):
    code=code.upper().replace('.IS','')
    period=period if period in {'1mo','3mo','6mo','1y','2y','5y'} else '1y'
    interval=interval if interval in {'15m','30m','60m','1d','1wk'} else '1d'
    if interval in {'15m','30m'} and period not in {'1mo'}:
        period='1mo'
    if interval=='60m' and period in {'1y','2y','5y'}:
        period='6mo'

    key=f'{code}:{period}:{interval}'
    now=time.time()
    with _LOCK:
        hit=_CHART_CACHE.get(key)
        if hit and now-hit[0] < 180:
            return hit[1]

    symbol=code if code.startswith('^') or '=' in code or '.' in code or '-' in code else code+'.IS'
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
    r=requests.get(
        url,
        params={'range':period,'interval':interval,'includePrePost':'false','events':'div,splits'},
        headers={'User-Agent':'Mozilla/5.0 BIST-AI-Terminal/3.1'},
        timeout=20
    )
    r.raise_for_status()
    result=r.json().get('chart',{}).get('result') or []
    if not result:
        raise ValueError('Yahoo returned no chart result')

    obj=result[0]
    ts=obj.get('timestamp') or []
    q=obj['indicators']['quote'][0]
    rows=[]
    for i,t in enumerate(ts):
        try:
            o,h,l,c,v=q['open'][i],q['high'][i],q['low'][i],q['close'][i],q['volume'][i]
            if None in (o,h,l,c): continue
            tm=int(t) if interval not in {'1d','1wk'} else time.strftime('%Y-%m-%d',time.gmtime(t))
            rows.append({
                'time':tm,'open':round(float(o),4),'high':round(float(h),4),
                'low':round(float(l),4),'close':round(float(c),4),'volume':int(v or 0)
            })
        except Exception:
            continue

    base=pd.DataFrame(rows)
    if base.empty:
        raise ValueError('No usable candles')
    calc=base.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
    ind=indicator_frame(calc)
    adv=advanced_series(calc)
    structure=analyze_structure(calc)

    data={
        'ticker':code,'period':period,'interval':interval,
        'currency':(obj.get('meta') or {}).get('currency','TRY'),
        'candles':rows,
        'ema20':_series(rows,ind['EMA20']),
        'ema50':_series(rows,ind['EMA50']),
        'ema200':_series(rows,ind['EMA200']),
        'bb_upper':_series(rows,ind['BB_UPPER']),
        'bb_mid':_series(rows,ind['BB_MID']),
        'bb_lower':_series(rows,ind['BB_LOWER']),
        'rsi':_series(rows,ind['RSI14'],2),
        'stoch_k':_series(rows,ind['STOCH_RSI_K'],2),
        'stoch_d':_series(rows,ind['STOCH_RSI_D'],2),
        'macd':_series(rows,ind['MACD'],5),
        'macd_signal':_series(rows,ind['MACD_SIGNAL'],5),
        'macd_hist':_series(rows,ind['MACD_HIST'],5),
        'adx':_series(rows,ind['ADX14'],2),
        'plus_di':_series(rows,ind['PLUS_DI'],2),
        'minus_di':_series(rows,ind['MINUS_DI'],2),
        'mfi':_series(rows,ind['MFI14'],2),
        'atr_pct':_series(rows,ind['ATR_PCT'],2),
        'supertrend_up':[{'time':row['time'],'value':round(float(v),4)} for row,v,b in zip(rows,adv['supertrend'],adv['supertrend_bull']) if pd.notna(v) and bool(b)],
        'supertrend_down':[{'time':row['time'],'value':round(float(v),4)} for row,v,b in zip(rows,adv['supertrend'],adv['supertrend_bull']) if pd.notna(v) and not bool(b)],
        'tenkan':_series(rows,adv['tenkan']),
        'kijun':_series(rows,adv['kijun']),
        'ichimoku_a':_series(rows,adv['ichimoku_a']),
        'ichimoku_b':_series(rows,adv['ichimoku_b']),
        'structure':structure,
    }
    last=ind.iloc[-1]
    data['indicators']={
        'rsi':round(float(last['RSI14']),1) if pd.notna(last['RSI14']) else None,
        'stoch_k':round(float(last['STOCH_RSI_K']),1) if pd.notna(last['STOCH_RSI_K']) else None,
        'stoch_d':round(float(last['STOCH_RSI_D']),1) if pd.notna(last['STOCH_RSI_D']) else None,
        'macd':round(float(last['MACD']),4) if pd.notna(last['MACD']) else None,
        'macd_signal':round(float(last['MACD_SIGNAL']),4) if pd.notna(last['MACD_SIGNAL']) else None,
        'macd_hist':round(float(last['MACD_HIST']),4) if pd.notna(last['MACD_HIST']) else None,
        'adx':round(float(last['ADX14']),1) if pd.notna(last['ADX14']) else None,
        'mfi':round(float(last['MFI14']),1) if pd.notna(last['MFI14']) else None,
        'atr_pct':round(float(last['ATR_PCT']),2) if pd.notna(last['ATR_PCT']) else None,
        'bb_pct':round(float(last['BB_PCT']),1) if pd.notna(last['BB_PCT']) else None,
    }

    with _LOCK:
        _CHART_CACHE[key]=(now,data)
    return data

def _rows_to_df(rows):
    if not rows:
        return pd.DataFrame()
    df=pd.DataFrame(rows)
    return df.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})

def _resample_4h(rows):
    if not rows:
        return pd.DataFrame()
    df=pd.DataFrame(rows)
    if df.empty or not isinstance(df.iloc[0]['time'],(int,float)):
        return pd.DataFrame()
    dt=pd.to_datetime(df['time'],unit='s',utc=True)
    df=df.set_index(dt)
    out=df.resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
    return out.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})

def _tf_summary(df, label):
    if df is None or df.empty or len(df)<30:
        return {'timeframe':label,'status':'NO_DATA'}
    sc=score_frame(df)
    if not sc:
        return {'timeframe':label,'status':'NO_DATA'}
    return {
        'timeframe':label,'status':'OK','score':sc.get('short_score'),'long_score':sc.get('long_score'),
        'signal':sc.get('short_signal'),'trend':sc.get('trend'),'rsi':sc.get('rsi'),'stoch':sc.get('stoch_rsi_k'),
        'macd_hist':sc.get('macd_hist'),'adx':sc.get('adx'),'mfi':sc.get('mfi'),'supertrend':sc.get('supertrend'),
        'ichimoku':sc.get('ichimoku'),'rsi_divergence':sc.get('rsi_divergence'),'macd_divergence':sc.get('macd_divergence'),
        'squeeze':sc.get('bollinger_squeeze'),'cross_event':sc.get('cross_event')
    }

def multi_timeframe(code):
    frames=[]
    specs=[
        ('15D','1mo','15m'),
        ('1S','3mo','60m'),
        ('1G','1y','1d'),
        ('1H','5y','1wk')
    ]
    hourly_rows=[]
    for label,period,interval in specs:
        try:
            d=yahoo_chart(code,period=period,interval=interval)
            rows=d.get('candles',[])
            if interval=='60m':
                hourly_rows=rows
            frames.append(_tf_summary(_rows_to_df(rows),label))
        except Exception:
            frames.append({'timeframe':label,'status':'ERROR'})
    try:
        frames.insert(2,_tf_summary(_resample_4h(hourly_rows),'4S'))
    except Exception:
        frames.insert(2,{'timeframe':'4S','status':'ERROR'})
    valid=[x for x in frames if x.get('status')=='OK']
    bull=sum(1 for x in valid if x.get('score',0)>=60 and x.get('supertrend')=='BULLISH')
    bear=sum(1 for x in valid if x.get('score',100)<45 and x.get('supertrend')=='BEARISH')
    consensus='BULLISH' if valid and bull>=max(2,len(valid)//2+1) else ('BEARISH' if valid and bear>=max(2,len(valid)//2+1) else 'MIXED')
    return {'ticker':code.upper(),'consensus':consensus,'bullish_frames':bull,'bearish_frames':bear,'frames':frames}

def market_overview():
    out={'mode':'LIVE / YAHOO','updated':time.strftime('%d.%m.%Y %H:%M:%S'),'global_score':50,'regime':'NÖTR','fear':50,'breadth':0,'advancers':0,'decliners':0,'unchanged':0}
    symbols=[
        ('xu100','XU100'),('usdtry','TRY=X'),('eurtry','EURTRY=X'),('sp500','^GSPC'),
        ('nasdaq','^IXIC'),('dxy','DX-Y.NYB'),('us10y','^TNX'),('gold','GC=F'),('oil','CL=F')
    ]
    ok=0
    for key,sym in symbols:
        try:
            d=yahoo_chart(sym,period='1mo',interval='1d')
            if d and len(d['candles'])>=2:
                a,b=d['candles'][-1]['close'],d['candles'][-2]['close']
                out[key]=a
                out[key+'_change']=round((a/b-1)*100,2)
                ok+=1
            else:
                out[key]=0
                out[key+'_change']=0
        except Exception:
            out[key]=0
            out[key+'_change']=0

    score=50
    score += 12 if out.get('sp500_change',0)>0 else -10
    score += 10 if out.get('nasdaq_change',0)>0 else -8
    score += 14 if out.get('xu100_change',0)>0 else -12
    score += -8 if out.get('usdtry_change',0)>0.35 else (4 if out.get('usdtry_change',0)<0 else 0)
    score += -5 if out.get('us10y_change',0)>1 else 2
    score += -4 if out.get('dxy_change',0)>0.5 else 2
    score=int(max(0,min(100,score)))
    out['global_score']=score
    out['regime']='RISK-ON / BULL' if score>=62 else ('RISK-OFF / BEAR' if score<=38 else 'NÖTR / TRANSITION')
    out['mode']='LIVE / YAHOO' if ok>=3 else ('PARTIAL / YAHOO' if ok else 'DATA UNAVAILABLE')
    return out
