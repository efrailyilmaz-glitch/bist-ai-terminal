from __future__ import annotations
import math
from typing import List
import numpy as np
import pandas as pd
import yfinance as yf

def _clean_series(s):
    return pd.to_numeric(s,errors='coerce').dropna()

def analyze_portfolio(codes:List[str]):
    codes=list(dict.fromkeys([x.upper().replace('.IS','') for x in codes if x]))[:12]
    if not codes:return {'status':'NO_CODES'}
    syms=[x+'.IS' for x in codes]+['XU100.IS']
    try:
        raw=yf.download(syms,period='1y',interval='1d',group_by='column',auto_adjust=True,threads=True,progress=False,timeout=25)
        if raw is None or raw.empty:return {'status':'NO_DATA'}
        close=raw['Close'] if isinstance(raw.columns,pd.MultiIndex) and 'Close' in raw.columns.get_level_values(0) else raw
        if isinstance(close,pd.Series):close=close.to_frame()
        close=close.dropna(how='all')
        rename={c:c.replace('.IS','') for c in close.columns}
        close=close.rename(columns=rename)
        valid=[c for c in codes if c in close.columns and close[c].notna().sum()>80]
        if not valid:return {'status':'NO_DATA'}
        rets=close[valid].pct_change().dropna(how='all')
        bench=close['XU100'] if 'XU100' in close.columns else (close['XU100.IS'] if 'XU100.IS' in close.columns else None)
        weights=np.array([1/len(valid)]*len(valid))
        cov=rets.cov()*252
        port_var=float(weights@cov.values@weights.T)
        port_vol=math.sqrt(max(0,port_var))*100
        port_ret=rets.mean().values@weights*252*100
        sharpe=(port_ret/100)/(port_vol/100) if port_vol else 0
        p=(rets.fillna(0).values@weights)
        eq=pd.Series((1+p).cumprod(),index=rets.index)
        dd=eq/eq.cummax()-1
        corr=rets.corr()
        off=[]
        for i in range(len(valid)):
            for j in range(i+1,len(valid)):off.append(float(corr.iloc[i,j]))
        avg_corr=float(np.mean(off)) if off else 0
        div_score=max(0,min(100,round((1-avg_corr)*100)))
        marginal=cov.values@weights
        contrib=weights*marginal/max(port_var,1e-12)
        risks=[]
        for i,c in enumerate(valid):
            s=rets[c].dropna()
            vol=float(s.std()*np.sqrt(252)*100)
            beta=None
            if bench is not None:
                bret=_clean_series(bench.pct_change())
                joined=pd.concat([s,bret],axis=1).dropna()
                if len(joined)>30 and joined.iloc[:,1].var()>0:
                    beta=float(joined.iloc[:,0].cov(joined.iloc[:,1])/joined.iloc[:,1].var())
            risks.append({'ticker':c,'weight_pct':round(weights[i]*100,1),'volatility_pct':round(vol,1),
                          'beta_xu100':None if beta is None else round(beta,2),'risk_contribution_pct':round(float(contrib[i]*100),1)})
        matrix=[{'ticker':r,**{c:round(float(corr.loc[r,c]),2) for c in valid}} for r in valid]
        return {'status':'OK','tickers':valid,'annual_return_pct':round(float(port_ret),1),'annual_volatility_pct':round(float(port_vol),1),
                'sharpe_proxy':round(float(sharpe),2),'max_drawdown_pct':round(float(dd.min()*100),1),
                'avg_correlation':round(avg_corr,2),'diversification_score':div_score,'risk_rows':risks,'correlation':matrix,
                'note':'Equal-weight historical proxy; not a forecast.'}
    except Exception as e:
        return {'status':'ERROR','error':str(e)[:180]}
