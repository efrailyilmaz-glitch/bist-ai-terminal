from __future__ import annotations
import math, time, threading
import numpy as np
import pandas as pd
from .fundamentals import get_fundamentals
from .market_data import scan_codes, yahoo_rows
from .analyst_engine import trusted_research

_LOCK=threading.Lock();_CACHE={};TTL=15*60

def _v(x,d=None):
    try:
        if x is None:return d
        z=float(x)
        return d if math.isnan(z) or math.isinf(z) else z
    except Exception:return d

def _clip(x,a=0,b=100):return max(a,min(b,x))

def _score_high(v,bad,good):
    v=_v(v)
    if v is None:return None
    if v<=bad:return 0
    if v>=good:return 100
    return 100*(v-bad)/(good-bad)

def _score_low(v,good,bad):
    v=_v(v)
    if v is None:return None
    if v<=good:return 100
    if v>=bad:return 0
    return 100*(bad-v)/(bad-good)

def _avg(xs):
    xs=[float(x) for x in xs if x is not None and np.isfinite(x)]
    return None if not xs else sum(xs)/len(xs)

def _annual_snapshot(ticker_obj):
    out={'latest':{},'previous':{}}
    try:
        inc=ticker_obj.income_stmt
        bal=ticker_obj.balance_sheet
        cf=ticker_obj.cashflow
        cols=[]
        for df in (inc,bal,cf):
            if df is not None and not df.empty:
                for c in df.columns:
                    if c not in cols:cols.append(c)
        cols=sorted(cols,reverse=True)[:2]
        mapping={
          'revenue':(inc,['Total Revenue','Operating Revenue']),
          'net_income':(inc,['Net Income','Net Income Common Stockholders']),
          'ebit':(inc,['EBIT','Operating Income']),
          'gross_profit':(inc,['Gross Profit']),
          'operating_cash_flow':(cf,['Operating Cash Flow','Total Cash From Operating Activities']),
          'total_assets':(bal,['Total Assets']),
          'total_liabilities':(bal,['Total Liabilities Net Minority Interest','Total Liabilities']),
          'current_assets':(bal,['Current Assets','Total Current Assets']),
          'current_liabilities':(bal,['Current Liabilities','Total Current Liabilities']),
          'retained_earnings':(bal,['Retained Earnings']),
          'long_term_debt':(bal,['Long Term Debt And Capital Lease Obligation','Long Term Debt']),
          'shares':(bal,['Ordinary Shares Number','Share Issued'])
        }
        def row(df,names):
            if df is None or df.empty:return None
            for n in names:
                if n in df.index:return df.loc[n]
            return None
        for idx,col in enumerate(cols):
            dest=out['latest' if idx==0 else 'previous']
            for key,(df,names) in mapping.items():
                s=row(df,names);val=None
                try:
                    if s is not None and col in s.index:val=_v(s[col])
                except Exception:pass
                dest[key]=val
    except Exception:pass
    return out

def _piotroski(a):
    c=a.get('latest') or {};p=a.get('previous') or {}
    if not c or not p:return {'score':None,'max_score':9,'status':'NO_DATA','checks':[]}
    checks=[]
    def add(name,cond):
        if cond is None:return
        checks.append({'name':name,'pass':bool(cond)})
    ta=_v(c.get('total_assets'));pta=_v(p.get('total_assets'))
    ni=_v(c.get('net_income'));pni=_v(p.get('net_income'))
    ocf=_v(c.get('operating_cash_flow'));pocf=_v(p.get('operating_cash_flow'))
    roa=ni/ta if ni is not None and ta else None;proa=pni/pta if pni is not None and pta else None
    add('ROA pozitif',None if roa is None else roa>0)
    add('Faaliyet nakit akışı pozitif',None if ocf is None else ocf>0)
    add('ROA iyileşiyor',None if roa is None or proa is None else roa>proa)
    add('Nakit akışı net kârdan güçlü',None if ocf is None or ni is None else ocf>ni)
    ltd=_v(c.get('long_term_debt'));pltd=_v(p.get('long_term_debt'))
    add('Uzun borç/varlık düşüyor',None if ltd is None or pltd is None or not ta or not pta else ltd/ta<pltd/pta)
    ca=_v(c.get('current_assets'));cl=_v(c.get('current_liabilities'));pca=_v(p.get('current_assets'));pcl=_v(p.get('current_liabilities'))
    add('Cari oran iyileşiyor',None if None in (ca,cl,pca,pcl) or cl==0 or pcl==0 else ca/cl>pca/pcl)
    sh=_v(c.get('shares'));psh=_v(p.get('shares'));add('Yeni hisse seyrelmesi yok',None if sh is None or psh is None else sh<=psh*1.01)
    gp=_v(c.get('gross_profit'));rev=_v(c.get('revenue'));pgp=_v(p.get('gross_profit'));prev=_v(p.get('revenue'))
    add('Brüt marj iyileşiyor',None if None in (gp,rev,pgp,prev) or not rev or not prev else gp/rev>pgp/prev)
    add('Varlık devir hızı iyileşiyor',None if None in (rev,prev,ta,pta) or not ta or not pta else rev/ta>prev/pta)
    score=sum(1 for x in checks if x['pass'])
    return {'score':score,'max_score':len(checks),'status':'STRONG' if score>=7 else 'MID' if score>=4 else 'WEAK','checks':checks}

def _altman(f,a):
    sector=(f.get('sector') or '').lower()
    if any(x in sector for x in ['financial','bank','insurance','banka','sigorta']):
        return {'score':None,'status':'N/A FINANCIAL','note':'Altman Z finansal şirketler için uygun değildir.'}
    c=a.get('latest') or {}
    ta=_v(c.get('total_assets'));tl=_v(c.get('total_liabilities'));ca=_v(c.get('current_assets'));cl=_v(c.get('current_liabilities'));re=_v(c.get('retained_earnings'));ebit=_v(c.get('ebit'));rev=_v(c.get('revenue'));mc=_v(f.get('market_cap'))
    if None in (ta,tl,ca,cl,re,ebit,rev,mc) or not ta or not tl:return {'score':None,'status':'NO_DATA'}
    z=1.2*((ca-cl)/ta)+1.4*(re/ta)+3.3*(ebit/ta)+.6*(mc/tl)+1.0*(rev/ta)
    return {'score':round(z,2),'status':'SAFE' if z>2.99 else 'GREY' if z>=1.81 else 'DISTRESS','note':'Klasik Altman Z; sektör ve muhasebe farkları nedeniyle tek başına karar aracı değildir.'}

def fair_value_health(ticker):
    code=ticker.upper().replace('.IS','');now=time.time()
    with _LOCK:
        h=_CACHE.get(code)
        if h and now-h[0]<TTL:return h[1]
    tech=(scan_codes([code]) or [{}])[0];f=get_fundamentals(code);price=_v(tech.get('price')) or _v(f.get('current_price'))
    analyst=trusted_research(code,current_price=price,fundamentals=f)
    methods=[]
    eps=_v(f.get('trailing_eps'));bv=_v(f.get('book_value'));roe=_v(f.get('roe_pct'));growth=_v(f.get('earnings_growth_pct'));shares=_v(f.get('shares_outstanding'));fcf=_v(f.get('free_cash_flow'))
    if analyst.get('consensus_target'):methods.append({'method':'Analist Konsensüsü','value':round(_v(analyst['consensus_target']),2),'weight':1.2})
    if eps and eps>0 and bv and bv>0:methods.append({'method':'Graham Number','value':round(math.sqrt(22.5*eps*bv),2),'weight':.8})
    if eps and eps>0:
        justified_pe=_clip(10+max(-5,min(25,(growth or 0)*.35))+max(-2,min(8,(roe or 0)*.18)),8,28)
        methods.append({'method':'Kazanç Gücü','value':round(eps*justified_pe,2),'weight':1.0})
    if bv and bv>0:
        justified_pb=_clip(.9+max(0,min(3,(roe or 0)/12)),.7,4.2)
        methods.append({'method':'Defter Değeri / ROE','value':round(bv*justified_pb,2),'weight':.8})
    if fcf and shares and shares>0:
        fcfps=fcf/shares;multiple=_clip(12+max(-2,min(8,(growth or 0)*.18)),8,24)
        if fcfps>0:methods.append({'method':'FCF Kazanç Gücü','value':round(fcfps*multiple,2),'weight':1.0})
    vals=[x['value'] for x in methods if x.get('value') and x['value']>0]
    fair=round(float(np.median(vals)),2) if vals else None
    lo=round(float(np.percentile(vals,25)),2) if len(vals)>=2 else fair
    hi=round(float(np.percentile(vals,75)),2) if len(vals)>=2 else fair
    upside=round((fair/price-1)*100,1) if fair and price else None
    categories={
      'profitability':_avg([_score_high(f.get('roe_pct'),0,30),_score_high(f.get('roa_pct'),0,15),_score_high(f.get('profit_margin_pct'),0,22)]),
      'growth':_avg([_score_high(f.get('revenue_growth_pct'),-10,35),_score_high(f.get('earnings_growth_pct'),-15,40)]),
      'balance':_avg([_score_low(f.get('debt_to_equity'),.3,2.5),_score_high(f.get('current_ratio'),.7,2.0)]),
      'cashflow':_avg([100 if (f.get('free_cash_flow') or 0)>0 else 0 if f.get('free_cash_flow') is not None else None,_score_high(f.get('fcf_conversion_pct'),0,100)]),
      'valuation':f.get('value_score'),
      'momentum':_avg([tech.get('short_score'),tech.get('long_score'),_score_high(tech.get('relative_strength_20'),-10,15)])
    }
    health_vals=[x for x in categories.values() if x is not None]
    health=round(sum(health_vals)/len(health_vals)) if health_vals else None
    try:
        import yfinance as yf
        annual=_annual_snapshot(yf.Ticker(code+'.IS'))
    except Exception:annual={'latest':{},'previous':{}}
    piot=_piotroski(annual);alt=_altman(f,annual)
    out={'ticker':code,'price':price,'fair_value':fair,'fair_value_low':lo,'fair_value_high':hi,'fair_value_upside_pct':upside,'fair_value_methods':methods,
         'fair_value_confidence':min(100,20+len(methods)*16+(15 if analyst.get('coverage_count',0)>=2 else 0)),
         'health_score':health,'health_status':'EXCELLENT' if health is not None and health>=80 else 'GOOD' if health is not None and health>=65 else 'MIXED' if health is not None and health>=45 else 'WEAK',
         'health_categories':{k:(None if v is None else round(v)) for k,v in categories.items()},'piotroski':piot,'altman':alt,
         'analyst':analyst,'fundamentals':f,'technical':tech,'events':{'ex_dividend_date':f.get('ex_dividend_date'),'dividend_date':f.get('dividend_date'),'earnings_timestamp':f.get('earnings_timestamp')},
         'updated':time.strftime('%d.%m.%Y %H:%M:%S'),'note':'Fair Value bir tahmin aralığıdır; yöntemlerin hiçbiri gelecekteki fiyatı garanti etmez.'}
    with _LOCK:_CACHE[code]=(now,out)
    return out

def volume_profile(ticker,period='6mo',interval='1d',bins=28):
    raw=yahoo_rows(ticker,period=period,interval=interval);rows=raw.get('candles') or []
    if not rows:return {'ticker':ticker,'bins':[]}
    lo=min(x['low'] for x in rows);hi=max(x['high'] for x in rows)
    if hi<=lo:return {'ticker':ticker,'bins':[]}
    bins=max(12,min(int(bins),60));edges=np.linspace(lo,hi,bins+1);vol=np.zeros(bins)
    for x in rows:
        l=float(x['low']);h=float(x['high']);v=float(x.get('volume') or 0)
        idx=[i for i in range(bins) if edges[i]<=h and edges[i+1]>=l]
        if not idx:continue
        each=v/len(idx)
        for i in idx:vol[i]+=each
    total=float(vol.sum());poc=int(np.argmax(vol)) if total else 0
    order=list(np.argsort(vol)[::-1]);acc=0;va=[]
    for i in order:
        va.append(int(i));acc+=vol[i]
        if total and acc/total>=.70:break
    out=[]
    for i in range(bins):
        mid=(edges[i]+edges[i+1])/2
        out.append({'low':round(float(edges[i]),2),'high':round(float(edges[i+1]),2),'price':round(float(mid),2),'volume':round(float(vol[i]),0),'pct':round(float(vol[i]/total*100),2) if total else 0,'poc':i==poc,'value_area':i in va})
    return {'ticker':ticker.upper().replace('.IS',''),'period':period,'interval':interval,'bins':out,'poc_price':out[poc]['price'] if out else None,'value_area_pct':70,'note':'OHLCV proxy: hacim mumun low-high aralığına dağıtılır; gerçek tick/Level-2 volume profile değildir.'}
