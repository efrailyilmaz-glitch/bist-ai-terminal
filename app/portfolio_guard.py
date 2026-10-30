"""Portfolio-level concentration guard for prospective paper entries."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

def _clean_close(df):
    if df is None or df.empty or 'Close' not in df:return pd.Series(dtype=float)
    s=pd.to_numeric(df['Close'],errors='coerce').dropna()
    return s

def _ret(df):
    s=_clean_close(df)
    return s.pct_change().replace([np.inf,-np.inf],np.nan).dropna()

def _beta(a,b):
    x=pd.concat([a,b],axis=1).dropna()
    if len(x)<60:return None
    vb=float(x.iloc[:,1].var())
    return None if vb<=0 else float(x.iloc[:,0].cov(x.iloc[:,1])/vb)

def assess_frames(candidate,holdings,frames,candidate_side='BUY'):
    """Assess incremental concentration using signed exposure correlations."""
    candidate=candidate.upper().replace('.IS','')
    h={str(k).upper().replace('.IS',''):int(v) for k,v in (holdings or {}).items() if v}
    cr=_ret(frames.get(candidate))
    if len(cr)<80:return {'status':'UNKNOWN','risk_multiplier':.75,'flags':['CANDIDATE_HISTORY_MISSING']}
    bench=_ret(frames.get('XU100'));beta=_beta(cr,bench) if len(bench) else None
    vol=float(cr.std()*math.sqrt(252)*100) if len(cr)>20 else None
    csign=-1 if str(candidate_side).upper()=='SHORT' else 1
    signed=[];raw=[];recent_signed=[];downside_signed=[];tail_joint=[];missing=[]
    for code,qty in h.items():
        hr=_ret(frames.get(code))
        x=pd.concat([cr,hr],axis=1).dropna().tail(180)
        if len(x)<80:missing.append(code);continue
        corr=float(x.iloc[:,0].corr(x.iloc[:,1]))
        if not math.isfinite(corr):continue
        hsign=1 if qty>0 else -1;esign=csign*hsign
        raw.append((code,corr));signed.append((code,corr*esign))
        xr=x.tail(60);rc=float(xr.iloc[:,0].corr(xr.iloc[:,1])) if len(xr)>=40 else None
        if rc is not None and math.isfinite(rc):recent_signed.append((code,rc*esign))
        if len(bench):
            xb=pd.concat([cr,hr,bench],axis=1).dropna().tail(180)
            xd=xb[xb.iloc[:,2]<0]
            if len(xd)>=20:
                dc=float(xd.iloc[:,0].corr(xd.iloc[:,1]))
                if math.isfinite(dc):downside_signed.append((code,dc*esign))
        joint=float(((x.iloc[:,0]<-.02)&(x.iloc[:,1]*esign<-.02)).mean()) if len(x) else 0.0
        tail_joint.append((code,joint))
    max_signed=max((x[1] for x in signed),default=None)
    max_recent=max((x[1] for x in recent_signed),default=None)
    max_downside=max((x[1] for x in downside_signed),default=None)
    max_joint=max((x[1] for x in tail_joint),default=None)
    avg_signed=float(np.mean([x[1] for x in signed])) if signed else None
    cluster=sum(1 for _,x in signed if x>=.75)
    flags=[];status='CLEAR';rm=1.0
    if max_signed is not None and max_signed>=.90:flags.append('EXTREME_EFFECTIVE_CORRELATION')
    if max_recent is not None and max_recent>=.90:flags.append('RECENT_CORRELATION_SPIKE')
    if max_downside is not None and max_downside>=.85:flags.append('DOWNSIDE_CORRELATION_SPIKE')
    if max_joint is not None and max_joint>=.12:flags.append('JOINT_TAIL_LOSS')
    if cluster>=2:flags.append('CORRELATED_CLUSTER')
    if avg_signed is not None and len(signed)>=3 and avg_signed>=.72:flags.append('PORTFOLIO_FACTOR_CROWDING')
    if beta is not None and abs(beta)>=1.8:flags.append('HIGH_BETA')
    if vol is not None and vol>=70:flags.append('HIGH_VOLATILITY')
    if missing:flags.append('PARTIAL_HISTORY')
    hard=any(x in flags for x in ['EXTREME_EFFECTIVE_CORRELATION','PORTFOLIO_FACTOR_CROWDING','RECENT_CORRELATION_SPIKE','DOWNSIDE_CORRELATION_SPIKE']) or (cluster>=2 and beta is not None and abs(beta)>=1.5)
    if hard:status='BLOCK';rm=.0
    elif flags:status='CAUTION';rm=.65 if cluster or 'HIGH_BETA' in flags else .8
    return {'status':status,'risk_multiplier':rm,'flags':flags,
            'candidate_beta_xu100':None if beta is None else round(beta,3),
            'candidate_annual_vol_pct':None if vol is None else round(vol,2),
            'max_effective_corr':None if max_signed is None else round(max_signed,3),
            'max_recent60_effective_corr':None if max_recent is None else round(max_recent,3),
            'max_downside_effective_corr':None if max_downside is None else round(max_downside,3),
            'max_joint_tail_loss_rate':None if max_joint is None else round(max_joint,4),
            'avg_effective_corr':None if avg_signed is None else round(avg_signed,3),
            'high_corr_cluster_count':cluster,
            'pair_correlations':[{'ticker':k,'raw_corr':round(v,3),'effective_corr':round(dict(signed).get(k,v),3)} for k,v in raw],
            'note':'Uses 180d, recent-60d and benchmark-downside correlations plus joint tail losses. Estimates can still jump in stress; guard can only reduce or block exposure.'}

def portfolio_entry_guard(candidate,positions,candidate_side='BUY'):
    from .market_data import daily_frames
    holdings={k:int(v.get('quantity',0)) for k,v in (positions or {}).items()}
    codes=list(holdings)+[candidate,'XU100']
    try:
        frames=daily_frames(codes)
        return assess_frames(candidate,holdings,frames,candidate_side)
    except Exception as e:
        return {'status':'UNKNOWN','risk_multiplier':.75,'flags':['PORTFOLIO_GUARD_ERROR'],'error':str(e)[:120]}
