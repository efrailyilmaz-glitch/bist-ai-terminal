from __future__ import annotations
import math
from typing import List
import numpy as np
import pandas as pd
import yfinance as yf

TRADING_DAYS=252

def _clean_series(s):
    return pd.to_numeric(s,errors='coerce').dropna()

def _load(codes):
    syms=[x+'.IS' for x in codes]+['XU100.IS']
    raw=yf.download(syms,period='2y',interval='1d',group_by='column',auto_adjust=True,threads=True,progress=False,timeout=25)
    if raw is None or raw.empty:return None,None
    close=raw['Close'] if isinstance(raw.columns,pd.MultiIndex) and 'Close' in raw.columns.get_level_values(0) else raw
    if isinstance(close,pd.Series):close=close.to_frame()
    close=close.dropna(how='all')
    close=close.rename(columns={c:c.replace('.IS','') for c in close.columns})
    valid=[c for c in codes if c in close.columns and close[c].notna().sum()>120]
    if not valid:return None,None
    bench=close['XU100'] if 'XU100' in close.columns else None
    rets=close[valid].pct_change().dropna(how='all').fillna(0)
    return rets,bench

def _normalize(w):
    w=np.maximum(np.asarray(w,dtype=float),0)
    s=w.sum()
    return np.ones_like(w)/len(w) if s<=0 else w/s

def _weights(rets,method='equal'):
    cov=rets.cov().values*TRADING_DAYS
    n=cov.shape[0]
    method=(method or 'equal').lower()
    if method=='equal':
        return np.ones(n)/n
    if method=='inverse_vol':
        vol=np.sqrt(np.diag(cov));return _normalize(1/np.maximum(vol,1e-8))
    if method=='min_variance':
        try:
            inv=np.linalg.pinv(cov)
            return _normalize(inv@np.ones(n))
        except Exception:
            return np.ones(n)/n
    if method=='risk_parity':
        w=np.ones(n)/n
        for _ in range(300):
            var=max(float(w@cov@w),1e-12)
            mrc=cov@w
            rc=w*mrc/var
            target=np.ones(n)/n
            adj=np.sqrt(np.maximum(target,1e-8)/np.maximum(rc,1e-8))
            nw=_normalize(w*adj)
            if np.max(np.abs(nw-w))<1e-6:break
            w=.6*w+.4*nw
        return _normalize(w)
    return np.ones(n)/n

def _portfolio_stats(rets,weights):
    cov=rets.cov().values*TRADING_DAYS
    mu=rets.mean().values*TRADING_DAYS
    p=rets.values@weights
    eq=pd.Series((1+p).cumprod(),index=rets.index)
    dd=eq/eq.cummax()-1
    vol=math.sqrt(max(float(weights@cov@weights.T),0))
    ann=float(mu@weights)
    sharpe=ann/vol if vol else 0
    q=np.quantile(p,.05)
    cvar=p[p<=q].mean() if np.any(p<=q) else q
    marginal=cov@weights;var=max(float(weights@cov@weights),1e-12)
    rc=weights*marginal/var
    return {
      'annual_return_pct':ann*100,'annual_volatility_pct':vol*100,'sharpe_proxy':sharpe,
      'max_drawdown_pct':float(dd.min()*100),'var95_daily_pct':float(q*100),'cvar95_daily_pct':float(cvar*100),
      'risk_contribution_pct':rc*100,'portfolio_returns':p,'equity':eq
    }

def _monte_carlo(p,simulations=750,horizon=252,seed=43):
    rng=np.random.default_rng(seed);r=np.asarray(p,float);block=5;finals=[];dds=[]
    for _ in range(max(100,min(simulations,2000))):
        seq=[]
        while len(seq)<horizon:
            j=int(rng.integers(0,max(1,len(r)-block)))
            seq.extend(r[j:j+block].tolist())
        seq=np.array(seq[:horizon]);eq=np.cumprod(1+seq);dd=eq/np.maximum.accumulate(eq)-1
        finals.append((eq[-1]-1)*100);dds.append(dd.min()*100)
    return {'simulations':len(finals),'horizon_days':horizon,'return_p10':round(float(np.quantile(finals,.1)),1),
            'return_median':round(float(np.median(finals)),1),'return_p90':round(float(np.quantile(finals,.9)),1),
            'prob_positive_pct':round(float(np.mean(np.array(finals)>0)*100),1),
            'maxdd_median':round(float(np.median(dds)),1),'maxdd_p10':round(float(np.quantile(dds,.1)),1)}

def analyze_portfolio(codes:List[str],method='equal'):
    codes=list(dict.fromkeys([x.upper().replace('.IS','') for x in codes if x]))[:12]
    if not codes:return {'status':'NO_CODES'}
    try:
        rets,bench=_load(codes)
        if rets is None:return {'status':'NO_DATA'}
        valid=list(rets.columns);weights=_weights(rets,method);s=_portfolio_stats(rets,weights)
        corr=rets.corr();off=[float(corr.iloc[i,j]) for i in range(len(valid)) for j in range(i+1,len(valid))]
        avg_corr=float(np.mean(off)) if off else 0
        risks=[]
        bret=_clean_series(bench.pct_change()) if bench is not None else None
        for i,code in enumerate(valid):
            sr=rets[code].dropna();beta=None
            if bret is not None:
                joined=pd.concat([sr,bret],axis=1).dropna()
                if len(joined)>30 and joined.iloc[:,1].var()>0:
                    beta=float(joined.iloc[:,0].cov(joined.iloc[:,1])/joined.iloc[:,1].var())
            risks.append({'ticker':code,'weight_pct':round(float(weights[i]*100),1),
                          'volatility_pct':round(float(sr.std()*np.sqrt(TRADING_DAYS)*100),1),
                          'beta_xu100':None if beta is None else round(beta,2),
                          'risk_contribution_pct':round(float(s['risk_contribution_pct'][i]),1)})
        matrix=[{'ticker':r,**{cc:round(float(corr.loc[r,cc]),2) for cc in valid}} for r in valid]
        stress_beta=sum((x.get('beta_xu100') or 1)*x['weight_pct']/100 for x in risks)
        stress={'xu100_minus_5_estimated_pct':round(-5*stress_beta,1),
                'xu100_minus_10_estimated_pct':round(-10*stress_beta,1),
                'volatility_shock_estimated_pct':round(-1.5*s['annual_volatility_pct']/math.sqrt(TRADING_DAYS),1)}
        mc=_monte_carlo(s['portfolio_returns'])
        return {'status':'OK','method':method,'tickers':valid,'annual_return_pct':round(s['annual_return_pct'],1),
                'annual_volatility_pct':round(s['annual_volatility_pct'],1),'sharpe_proxy':round(s['sharpe_proxy'],2),
                'max_drawdown_pct':round(s['max_drawdown_pct'],1),'var95_daily_pct':round(s['var95_daily_pct'],2),
                'cvar95_daily_pct':round(s['cvar95_daily_pct'],2),'avg_correlation':round(avg_corr,2),
                'diversification_score':max(0,min(100,round((1-avg_corr)*100))),'risk_rows':risks,'correlation':matrix,
                'stress':stress,'monte_carlo':mc,'note':f'{method} historical proxy; not a forecast.'}
    except Exception as e:
        return {'status':'ERROR','error':str(e)[:180]}

def compare_allocations(codes:List[str]):
    rows=[]
    for method in ['equal','inverse_vol','min_variance','risk_parity']:
        r=analyze_portfolio(codes,method)
        if r.get('status')=='OK':
            rows.append({k:v for k,v in r.items() if k in ['method','annual_return_pct','annual_volatility_pct','sharpe_proxy','max_drawdown_pct','var95_daily_pct','cvar95_daily_pct','diversification_score']})
    return {'rows':rows}
