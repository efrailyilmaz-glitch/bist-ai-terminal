from __future__ import annotations
import math, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List
import numpy as np
import pandas as pd
import yfinance as yf

_LOCK=threading.Lock()
_CACHE={}
TTL=6*3600

def _clean(v):
    try:
        if v is None: return None
        x=float(v)
        if math.isnan(x) or math.isinf(x): return None
        return x
    except Exception:
        return None

def _pct(v):
    x=_clean(v)
    return None if x is None else x*100

def _de_ratio(v):
    x=_clean(v)
    if x is None: return None
    return x/100 if abs(x)>10 else x

def _score_low(v, good, bad):
    v=_clean(v)
    if v is None: return None
    if v<=good:return 100.0
    if v>=bad:return 0.0
    return 100*(bad-v)/(bad-good)

def _score_high(v,bad,good):
    v=_clean(v)
    if v is None:return None
    if v<=bad:return 0.0
    if v>=good:return 100.0
    return 100*(v-bad)/(good-bad)

def _avg(vals):
    vals=[float(x) for x in vals if x is not None and np.isfinite(x)]
    return None if not vals else sum(vals)/len(vals)

def _row(df:pd.DataFrame,names:List[str]):
    if df is None or df.empty:return None
    for n in names:
        if n in df.index:return df.loc[n]
    return None

def _quarterly(t:yf.Ticker):
    result=[]
    try:
        inc=t.quarterly_income_stmt
        bal=t.quarterly_balance_sheet
        cf=t.quarterly_cashflow
        cols=[]
        for df in (inc,bal,cf):
            if df is not None and not df.empty:
                cols.extend(list(df.columns))
        uniq=[]
        for c in cols:
            if c not in uniq:uniq.append(c)
        uniq=sorted(uniq,reverse=True)[:6]
        series={
          'revenue':_row(inc,['Total Revenue','Operating Revenue']),
          'net_income':_row(inc,['Net Income','Net Income Common Stockholders']),
          'operating_income':_row(inc,['Operating Income','EBIT']),
          'ebitda':_row(inc,['EBITDA','Normalized EBITDA']),
          'free_cash_flow':_row(cf,['Free Cash Flow']),
          'operating_cash_flow':_row(cf,['Operating Cash Flow','Total Cash From Operating Activities']),
          'total_debt':_row(bal,['Total Debt']),
          'cash':_row(bal,['Cash Cash Equivalents And Short Term Investments','Cash And Cash Equivalents'])
        }
        for col in uniq:
            item={'period':str(getattr(col,'date',lambda:col)()) if hasattr(col,'date') else str(col)[:10]}
            anyv=False
            for key,s in series.items():
                val=None
                try:
                    if s is not None and col in s.index:val=_clean(s[col])
                except Exception:pass
                item[key]=val
                anyv=anyv or val is not None
            if anyv:result.append(item)
    except Exception:
        pass
    return result

def _compute_scores(m:Dict):
    pe=m.get('trailing_pe'); pb=m.get('price_to_book'); ev_ebitda=m.get('ev_to_ebitda')
    ps=m.get('price_to_sales'); fcf_yield=m.get('fcf_yield')
    value=_avg([
        _score_low(pe,8,35),_score_low(pb,1,6),_score_low(ev_ebitda,5,22),
        _score_low(ps,0.8,7),_score_high(fcf_yield,-2,10)
    ])
    quality=_avg([
        _score_high(m.get('roe_pct'),0,30),_score_high(m.get('roa_pct'),0,15),
        _score_high(m.get('operating_margin_pct'),0,25),_score_high(m.get('profit_margin_pct'),0,20),
        100 if (m.get('free_cash_flow') or 0)>0 else (0 if m.get('free_cash_flow') is not None else None)
    ])
    growth=_avg([
        _score_high(m.get('revenue_growth_pct'),-10,35),
        _score_high(m.get('earnings_growth_pct'),-15,40)
    ])
    de=m.get('debt_to_equity')
    current=m.get('current_ratio')
    balance=_avg([
        _score_low(de,0.3,2.5),
        _score_high(current,0.7,2.0),
        100 if (m.get('total_cash') or 0)>(m.get('total_debt') or 0) else (35 if m.get('total_cash') is not None and m.get('total_debt') is not None else None)
    ])
    shareholder=_avg([
        _score_high(m.get('dividend_yield_pct'),0,6),
        _score_low(m.get('payout_ratio_pct'),80,150) if m.get('payout_ratio_pct') is not None else None
    ])
    categories={'value':value,'quality':quality,'growth':growth,'balance':balance,'shareholder':shareholder}
    weights={'value':.22,'quality':.28,'growth':.22,'balance':.20,'shareholder':.08}
    present=[k for k,v in categories.items() if v is not None]
    if not present:
        total=None
    else:
        den=sum(weights[k] for k in present)
        total=sum(categories[k]*weights[k] for k in present)/den
    metric_keys=['trailing_pe','price_to_book','ev_to_ebitda','roe_pct','roa_pct','operating_margin_pct','profit_margin_pct','revenue_growth_pct','earnings_growth_pct','debt_to_equity','current_ratio','free_cash_flow','dividend_yield_pct']
    coverage=round(100*sum(1 for k in metric_keys if m.get(k) is not None)/len(metric_keys))
    return {
      'fundamental_score':None if total is None else round(total),
      'value_score':None if value is None else round(value),
      'quality_score':None if quality is None else round(quality),
      'growth_score':None if growth is None else round(growth),
      'balance_score':None if balance is None else round(balance),
      'shareholder_score':None if shareholder is None else round(shareholder),
      'coverage_pct':coverage
    }

def get_fundamentals(ticker:str,force:bool=False)->Dict:
    code=ticker.upper().replace('.IS','')
    now=time.time()
    with _LOCK:
        hit=_CACHE.get(code)
        if hit and not force and now-hit[0]<TTL:return hit[1]
    symbol=code+'.IS'
    out={'ticker':code,'source':'YAHOO','status':'NO_DATA'}
    try:
        t=yf.Ticker(symbol)
        info=t.info or {}
        market_cap=_clean(info.get('marketCap'))
        fcf=_clean(info.get('freeCashflow'))
        m={
          'ticker':code,'name':info.get('longName') or info.get('shortName') or code,
          'sector':info.get('sector'),'industry':info.get('industry'),'currency':info.get('currency') or 'TRY',
          'market_cap':market_cap,'enterprise_value':_clean(info.get('enterpriseValue')),
          'trailing_pe':_clean(info.get('trailingPE')),'forward_pe':_clean(info.get('forwardPE')),
          'price_to_book':_clean(info.get('priceToBook')),'price_to_sales':_clean(info.get('priceToSalesTrailing12Months')),
          'ev_to_ebitda':_clean(info.get('enterpriseToEbitda')),'peg_ratio':_clean(info.get('pegRatio')),
          'roe_pct':_pct(info.get('returnOnEquity')),'roa_pct':_pct(info.get('returnOnAssets')),
          'gross_margin_pct':_pct(info.get('grossMargins')),'operating_margin_pct':_pct(info.get('operatingMargins')),
          'profit_margin_pct':_pct(info.get('profitMargins')),
          'revenue_growth_pct':_pct(info.get('revenueGrowth')),'earnings_growth_pct':_pct(info.get('earningsGrowth')),
          'debt_to_equity':_de_ratio(info.get('debtToEquity')),'current_ratio':_clean(info.get('currentRatio')),'quick_ratio':_clean(info.get('quickRatio')),
          'free_cash_flow':fcf,'operating_cash_flow':_clean(info.get('operatingCashflow')),
          'total_cash':_clean(info.get('totalCash')),'total_debt':_clean(info.get('totalDebt')),
          'fcf_yield':None if not market_cap or fcf is None else fcf/market_cap*100,
          'dividend_yield_pct':_pct(info.get('dividendYield')),'payout_ratio_pct':_pct(info.get('payoutRatio')),
          'beta':_clean(info.get('beta')),'shares_outstanding':_clean(info.get('sharesOutstanding')),
          'target_mean_price':_clean(info.get('targetMeanPrice')),'analyst_count':_clean(info.get('numberOfAnalystOpinions')),
          'updated':time.strftime('%d.%m.%Y %H:%M:%S')
        }
        m.update(_compute_scores(m))
        m['quarterly']=_quarterly(t)
        m['status']='OK' if m['coverage_pct']>=15 else 'PARTIAL'
        out=m
    except Exception as e:
        out.update({'error':str(e)[:180],'updated':time.strftime('%d.%m.%Y %H:%M:%S')})
    with _LOCK:_CACHE[code]=(now,out)
    return out

def factor_screen(codes:List[str])->Dict:
    codes=list(dict.fromkeys([x.upper().replace('.IS','') for x in codes if x]))[:24]
    rows=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        fut={ex.submit(get_fundamentals,c):c for c in codes}
        for f in as_completed(fut):
            try:
                r=f.result()
                if r.get('status') in {'OK','PARTIAL'}:rows.append(r)
            except Exception:pass
    # Sector-relative percentile on available sample, not the full exchange.
    groups={}
    for r in rows:
        groups.setdefault(r.get('sector') or 'Unknown',[]).append(r)
    for sector,grp in groups.items():
        vals=sorted([x['fundamental_score'] for x in grp if x.get('fundamental_score') is not None])
        for r in grp:
            v=r.get('fundamental_score')
            if v is None or len(vals)<2:r['sector_percentile']=None
            else:r['sector_percentile']=round(100*sum(1 for x in vals if x<=v)/len(vals))
            r['peer_sample_size']=len(grp)
    rows.sort(key=lambda x:(x.get('fundamental_score') is not None,x.get('fundamental_score') or -1),reverse=True)
    return {'requested':len(codes),'received':len(rows),'rows':rows,'scope':'available sample; not full-sector consensus'}
