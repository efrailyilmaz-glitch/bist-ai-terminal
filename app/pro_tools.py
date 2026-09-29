from __future__ import annotations
import io, math, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
from .market_data import yahoo_rows, scan_codes
from .fundamentals import get_fundamentals
from .universe import get_universe
from .premium_engine import fair_value_health

_LOCK=threading.Lock();_CACHE={};TTL=20*60

def _v(x,d=None):
    try:
        if x is None:return d
        z=float(x);return d if math.isnan(z) or math.isinf(z) else z
    except Exception:return d
def _safe_div(a,b):
    a=_v(a);b=_v(b)
    return None if a is None or b in (None,0) else a/b
def _df(ticker,period='2y',interval='1d'):
    d=yahoo_rows(ticker,period=period,interval=interval);rows=d.get('candles') or []
    if not rows:return None,rows
    return pd.DataFrame(rows).rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'}),rows

def technical_pro(ticker):
    code=ticker.upper().replace('.IS','');key='techpro:'+code;now=time.time()
    with _LOCK:
        h=_CACHE.get(key)
        if h and now-h[0]<TTL:return h[1]
    df,rows=_df(code,'2y','1d')
    if df is None or len(df)<60:return {'ticker':code,'status':'NO_DATA'}
    h=df['High'].astype(float);l=df['Low'].astype(float);c=df['Close'].astype(float);v=df['Volume'].fillna(0).astype(float)
    typical=(h+l+c)/3
    pv=typical*v
    vwap20=(pv.rolling(20).sum()/v.rolling(20).sum().replace(0,np.nan))
    ema20=c.ewm(span=20,adjust=False).mean()
    pc=c.shift(1);tr=pd.concat([(h-l).abs(),(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1);atr14=tr.ewm(alpha=1/14,adjust=False).mean()
    kel_up=ema20+2*atr14;kel_lo=ema20-2*atr14
    don20h=h.rolling(20).max();don20l=l.rolling(20).min();don55h=h.rolling(55).max();don55l=l.rolling(55).min()
    chand_long=h.rolling(22).max()-3*atr14
    # Anchored VWAP from the lowest low in the last 120 sessions.
    sub=df.tail(120);anchor_pos=int(sub['Low'].astype(float).values.argmin());anchor_idx=len(df)-len(sub)+anchor_pos
    av_num=pv.iloc[anchor_idx:].cumsum();av_den=v.iloc[anchor_idx:].cumsum().replace(0,np.nan);avwap=av_num/av_den
    # Auto Fibonacci over last 120 sessions.
    hi=float(sub['High'].max());lo=float(sub['Low'].min());rng=max(1e-9,hi-lo)
    trend_up=int(sub['High'].idxmax())>int(sub['Low'].idxmin())
    fib={}
    for r in [0,0.236,0.382,0.5,0.618,0.786,1]:
        level=hi-r*rng if trend_up else lo+r*rng
        fib[str(r)]=round(float(level),2)
    prev=df.iloc[-2];P=(float(prev.High)+float(prev.Low)+float(prev.Close))/3
    piv={'P':P,'R1':2*P-float(prev.Low),'S1':2*P-float(prev.High),'R2':P+(float(prev.High)-float(prev.Low)),'S2':P-(float(prev.High)-float(prev.Low))}
    price=float(c.iloc[-1]);atr=float(atr14.iloc[-1]);av=float(avwap.iloc[-1]) if len(avwap) and np.isfinite(avwap.iloc[-1]) else None
    align=0;signals=[]
    if price>float(vwap20.iloc[-1]):align+=1;signals.append('VWAP20 üstü')
    if av and price>av:align+=1;signals.append('Anchored VWAP üstü')
    if price>float(don20h.shift(1).iloc[-1]):align+=1;signals.append('Donchian20 breakout')
    if price>float(chand_long.iloc[-1]):align+=1;signals.append('Chandelier trend koruyor')
    if price>float(ema20.iloc[-1]):align+=1;signals.append('EMA20 üstü')
    out={'ticker':code,'status':'OK','price':round(price,2),'vwap20':round(float(vwap20.iloc[-1]),2),'anchored_vwap':None if av is None else round(av,2),
         'anchor_date':rows[anchor_idx]['time'],'atr14':round(atr,2),'atr_pct':round(atr/price*100,2) if price else None,
         'keltner_upper':round(float(kel_up.iloc[-1]),2),'keltner_lower':round(float(kel_lo.iloc[-1]),2),
         'donchian20_high':round(float(don20h.iloc[-1]),2),'donchian20_low':round(float(don20l.iloc[-1]),2),
         'donchian55_high':round(float(don55h.iloc[-1]),2),'donchian55_low':round(float(don55l.iloc[-1]),2),
         'chandelier_long_stop':round(float(chand_long.iloc[-1]),2),'pivot':{k:round(float(x),2) for k,x in piv.items()},
         'fib':fib,'alignment_score':round(align/5*100),'signals':signals,
         'note':'VWAP is rolling daily OHLCV VWAP; anchored VWAP uses the lowest low in the latest 120 sessions as a transparent automatic anchor.'}
    with _LOCK:_CACHE[key]=(now,out)
    return out

def _stmt_rows(t):
    try:
        inc=t.income_stmt;bal=t.balance_sheet;cf=t.cashflow
        cols=[]
        for d in (inc,bal,cf):
            if d is not None and not d.empty:
                for c in d.columns:
                    if c not in cols:cols.append(c)
        cols=sorted(cols,reverse=True)[:2]
        def val(df,names,col):
            if df is None or df.empty:return None
            for n in names:
                if n in df.index:
                    try:return _v(df.loc[n,col])
                    except Exception:return None
            return None
        out=[]
        for col in cols:
            out.append({
              'sales':val(inc,['Total Revenue','Operating Revenue'],col),'cogs':val(inc,['Cost Of Revenue','Reconciled Cost Of Revenue'],col),
              'gross_profit':val(inc,['Gross Profit'],col),'sga':val(inc,['Selling General And Administration'],col),
              'depr':val(cf,['Depreciation And Amortization','Depreciation'],col),'ocf':val(cf,['Operating Cash Flow'],col),
              'receivables':val(bal,['Accounts Receivable','Receivables'],col),'current_assets':val(bal,['Current Assets','Total Current Assets'],col),
              'ppe':val(bal,['Net PPE','Property Plant Equipment Net'],col),'total_assets':val(bal,['Total Assets'],col),
              'current_liabilities':val(bal,['Current Liabilities','Total Current Liabilities'],col),
              'total_liabilities':val(bal,['Total Liabilities Net Minority Interest','Total Liabilities'],col),
              'net_income':val(inc,['Net Income','Net Income Common Stockholders'],col),'ebit':val(inc,['EBIT','Operating Income'],col),
              'interest_expense':val(inc,['Interest Expense','Interest Expense Non Operating'],col)
            })
        return out
    except Exception:return []

def forensic_models(ticker):
    code=ticker.upper().replace('.IS','');key='forensic:'+code;now=time.time()
    with _LOCK:
        h=_CACHE.get(key)
        if h and now-h[0]<TTL:return h[1]
    f=get_fundamentals(code);sector=(f.get('sector') or '').lower()
    try:
        import yfinance as yf
        rows=_stmt_rows(yf.Ticker(code+'.IS'))
    except Exception:rows=[]
    beneish={'score':None,'status':'NO_DATA'};sloan={'score':None,'status':'NO_DATA'};dupont={};interest=None
    if len(rows)>=2:
        c,p=rows[0],rows[1]
        try:
            dsri=_safe_div(_safe_div(c['receivables'],c['sales']),_safe_div(p['receivables'],p['sales']))
            gm_c=_safe_div((c['sales']-c['cogs']) if c['sales'] is not None and c['cogs'] is not None else c['gross_profit'],c['sales'])
            gm_p=_safe_div((p['sales']-p['cogs']) if p['sales'] is not None and p['cogs'] is not None else p['gross_profit'],p['sales'])
            gmi=_safe_div(gm_p,gm_c);aqi=_safe_div(1-_safe_div(c['current_assets']+c['ppe'],c['total_assets']),1-_safe_div(p['current_assets']+p['ppe'],p['total_assets']))
            sgi=_safe_div(c['sales'],p['sales']);depi=_safe_div(_safe_div(p['depr'],p['depr']+p['ppe']),_safe_div(c['depr'],c['depr']+c['ppe']))
            sgai=_safe_div(_safe_div(c['sga'],c['sales']),_safe_div(p['sga'],p['sales']))
            lvgi=_safe_div(_safe_div(c['total_liabilities'],c['total_assets']),_safe_div(p['total_liabilities'],p['total_assets']))
            tata=_safe_div((c['net_income']-c['ocf']) if c['net_income'] is not None and c['ocf'] is not None else None,c['total_assets'])
            xs=[dsri,gmi,aqi,sgi,depi,sgai,lvgi,tata]
            if all(x is not None and np.isfinite(x) for x in xs):
                m=-4.84+.92*dsri+.528*gmi+.404*aqi+.892*sgi+.115*depi-.172*sgai+4.679*tata-.327*lvgi
                beneish={'score':round(float(m),2),'status':'LOWER_RISK' if m<-2.22 else 'GREY' if m<-1.78 else 'ELEVATED_RISK','threshold':-1.78,
                         'note':'Beneish M-Score is a screening flag, not proof of manipulation.'}
        except Exception:pass
        try:
            accr=_safe_div((c['net_income']-c['ocf']) if c['net_income'] is not None and c['ocf'] is not None else None,c['total_assets'])
            if accr is not None:sloan={'score':round(accr*100,2),'status':'GOOD' if accr<.05 else 'WATCH' if accr<.10 else 'WEAK','note':'Lower accruals are generally preferable.'}
        except Exception:pass
        try:
            margin=_safe_div(c['net_income'],c['sales']);turn=_safe_div(c['sales'],c['total_assets'])
            eq=(c['total_assets']-c['total_liabilities']) if c['total_assets'] is not None and c['total_liabilities'] is not None else None
            lev=_safe_div(c['total_assets'],eq)
            if None not in (margin,turn,lev):dupont={'net_margin':round(margin*100,2),'asset_turnover':round(turn,2),'equity_multiplier':round(lev,2),'roe_proxy_pct':round(margin*turn*lev*100,2)}
        except Exception:pass
        try:
            if c['interest_expense'] not in (None,0) and c['ebit'] is not None:interest=round(abs(c['ebit']/c['interest_expense']),2)
        except Exception:pass
    out={'ticker':code,'status':'OK','beneish':beneish,'sloan_accrual':sloan,'dupont':dupont,'interest_coverage':interest,
         'debt_to_equity':f.get('debt_to_equity'),'fcf_conversion_pct':f.get('fcf_conversion_pct'),
         'note':'Forensic models are accounting screens and may be less comparable for banks/insurers or inflation-accounting periods.'}
    if any(x in sector for x in ['financial','bank','insurance','banka','sigorta']):out['financial_sector_warning']=True
    with _LOCK:_CACHE[key]=(now,out)
    return out

def peer_comparison(ticker,peer_count=5):
    code=ticker.upper().replace('.IS','');key=f'peers:{code}:{peer_count}';now=time.time()
    with _LOCK:
        h=_CACHE.get(key)
        if h and now-h[0]<TTL:return h[1]
    target=get_fundamentals(code);sector=target.get('sector')
    universe=get_universe();scan=scan_codes([x['ticker'] for x in universe]);liquid=sorted(scan,key=lambda x:x.get('avg_value_turnover_20',0),reverse=True)[:70]
    peers=[]
    def load(r):
        f=get_fundamentals(r['ticker']);return r,f
    with ThreadPoolExecutor(max_workers=6) as ex:
        fut=[ex.submit(load,r) for r in liquid if r['ticker']!=code]
        for q in as_completed(fut):
            try:r,f=q.result()
            except Exception:continue
            if sector and f.get('sector')!=sector:continue
            peers.append((r,f))
            if len(peers)>=max(3,min(int(peer_count),8)):break
    target_scan=(scan_codes([code]) or [{}])[0]
    rows=[(target_scan,target)]
    rows.extend(peers)
    outrows=[]
    for r,f in rows:
        prem=fair_value_health(r.get('ticker') or code)
        outrows.append({'ticker':r.get('ticker') or code,'sector':f.get('sector'),'price':r.get('price'),'pe':f.get('trailing_pe'),'pb':f.get('price_to_book'),
          'ev_ebitda':f.get('ev_to_ebitda'),'roe_pct':f.get('roe_pct'),'revenue_growth_pct':f.get('revenue_growth_pct'),'earnings_growth_pct':f.get('earnings_growth_pct'),
          'debt_to_equity':f.get('debt_to_equity'),'fcf_yield':f.get('fcf_yield'),'fundamental_score':f.get('fundamental_score'),'health_score':prem.get('health_score'),
          'fair_value_upside_pct':prem.get('fair_value_upside_pct'),'rs20':r.get('relative_strength_20'),'long_score':r.get('long_score')})
    metrics=['pe','pb','ev_ebitda','roe_pct','revenue_growth_pct','earnings_growth_pct','debt_to_equity','fcf_yield','fundamental_score','health_score','fair_value_upside_pct','rs20','long_score']
    target_row=outrows[0];pct={}
    for m in metrics:
        vals=[_v(x.get(m)) for x in outrows if _v(x.get(m)) is not None]
        tv=_v(target_row.get(m))
        if tv is None or not vals:pct[m]=None;continue
        higher_better=m not in {'pe','pb','ev_ebitda','debt_to_equity'}
        rank=sum(1 for v in vals if v<=tv)/len(vals)*100
        pct[m]=round(rank if higher_better else 100-rank,1)
    result={'ticker':code,'sector':sector,'rows':outrows,'target_percentiles':pct,'peer_count':len(outrows)-1,'note':'Peers are selected from a liquid available sample with matching Yahoo sector classification.'}
    with _LOCK:_CACHE[key]=(now,result)
    return result

def compare_symbols(codes):
    codes=list(dict.fromkeys([x.upper().replace('.IS','') for x in codes if x]))[:8];out=[]
    for code in codes:
        df,rows=_df(code,'2y','1d')
        if df is None:continue
        c=df['Close'].astype(float)
        perf={}
        for n,label in [(21,'1m'),(63,'3m'),(126,'6m'),(252,'1y')]:
            perf[label]=round((c.iloc[-1]/c.iloc[-min(n,len(c))]-1)*100,2) if len(c)>2 else None
        tech=(scan_codes([code]) or [{}])[0];f=get_fundamentals(code);prem=fair_value_health(code)
        out.append({'ticker':code,'price':tech.get('price'),'performance':perf,'short_score':tech.get('short_score'),'long_score':tech.get('long_score'),'risk':tech.get('risk'),
                    'rs20':tech.get('relative_strength_20'),'pe':f.get('trailing_pe'),'pb':f.get('price_to_book'),'roe_pct':f.get('roe_pct'),'fundamental_score':f.get('fundamental_score'),
                    'health_score':prem.get('health_score'),'fair_value_upside_pct':prem.get('fair_value_upside_pct')})
    return {'rows':out}
