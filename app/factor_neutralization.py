"""V65 cross-sectional sector/factor neutralization.
Purifies challenger scores from broad momentum/volatility/trend exposures.
Sector neutralization is applied only when sector metadata coverage is sufficient.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

FACTORS=['ret_20','vol_20','ema50_gap']

def _z(s):
    x=pd.to_numeric(s,errors='coerce').astype(float)
    sd=float(x.std())
    return (x-float(x.mean()))/(sd if sd>1e-12 else 1.0)

def neutralize(frame,score_col='raw_score',sector_col='sector',min_rows=10,min_sector_coverage=.70):
    if frame is None or len(frame)<min_rows or score_col not in frame:
        return {'status':'INSUFFICIENT_SAMPLE','frame':frame,'flags':['NEUTRALIZATION_SAMPLE_TOO_SMALL']}
    df=frame.copy()
    usable=[f for f in FACTORS if f in df and pd.to_numeric(df[f],errors='coerce').notna().sum()>=min_rows]
    if len(usable)<2:
        return {'status':'INSUFFICIENT_FACTORS','frame':df,'flags':['FACTOR_METADATA_INCOMPLETE']}
    y=pd.to_numeric(df[score_col],errors='coerce').astype(float).fillna(0).values
    X=[np.ones(len(df))]
    factor_corr={}
    for f in usable:
        z=_z(df[f]).fillna(0).values
        X.append(z)
        factor_corr[f]=float(np.corrcoef(y,z)[0,1]) if np.std(y)>0 and np.std(z)>0 else 0.0
    flags=[]
    sector_coverage=0.0
    sectors_used=0
    if sector_col in df:
        sec=df[sector_col].fillna('').astype(str).str.strip()
        sector_coverage=float((sec!='').mean())
        if sector_coverage>=min_sector_coverage and sec[sec!=''].nunique()>=2:
            dummies=pd.get_dummies(sec.where(sec!='','UNKNOWN'),prefix='sector',dtype=float)
            # Drop one reference sector to avoid exact dummy collinearity with intercept.
            for col in list(dummies.columns)[1:]:
                X.append(dummies[col].values)
            sectors_used=max(0,len(dummies.columns)-1)
        else:
            flags.append('SECTOR_METADATA_INCOMPLETE')
    else:
        flags.append('SECTOR_METADATA_INCOMPLETE')
    mat=np.column_stack(X)
    beta=np.linalg.lstsq(mat,y,rcond=None)[0]
    fitted=mat@beta
    resid=y-fitted
    raw_var=float(np.var(y))
    r2=0.0 if raw_var<=1e-12 else max(0.0,min(1.0,1-float(np.var(resid))/raw_var))
    if np.std(resid)>1e-12:
        neutral=(resid-float(np.mean(resid)))/float(np.std(resid))
    else:
        neutral=np.zeros(len(resid))
    df['raw_score']=y
    df['score']=neutral
    neutral_corr={}
    for f in usable:
        z=_z(df[f]).fillna(0).values
        neutral_corr[f]=float(np.corrcoef(neutral,z)[0,1]) if np.std(neutral)>0 and np.std(z)>0 else 0.0
    max_raw=max([abs(x) for x in factor_corr.values()],default=0.0)
    max_neutral=max([abs(x) for x in neutral_corr.values()],default=0.0)
    if r2>=.65:flags.append('RAW_SCORE_FACTOR_CONCENTRATION')
    if max_neutral>.15:flags.append('RESIDUAL_FACTOR_EXPOSURE')
    status='PASS' if max_neutral<=.15 else 'CAUTION'
    return {'status':status,'frame':df,'flags':flags,'diagnostics':{
        'rows':len(df),'factors':usable,'sector_coverage_pct':round(sector_coverage*100,1),
        'sector_dummies_used':sectors_used,'raw_factor_r2':round(r2,4),
        'raw_factor_correlations':{k:round(v,4) for k,v in factor_corr.items()},
        'neutral_factor_correlations':{k:round(v,4) for k,v in neutral_corr.items()},
        'max_raw_abs_factor_corr':round(max_raw,4),'max_neutral_abs_factor_corr':round(max_neutral,4)},
        'policy':'Neutralization changes cross-sectional ranking only to remove broad factor/sector exposure; it never enables live execution.'}

def evaluate_history(history):
    rebs=(history or {}).get('rebalances') or []
    if not rebs:return {'status':'OBSERVE','reasons':['NO_NEUTRALIZATION_EVIDENCE']}
    latest=next((r for r in rebs if r.get('integrity_json')),None)
    if not latest:return {'status':'OBSERVE','reasons':['NEUTRALIZATION_METADATA_MISSING']}
    import json
    try:meta=json.loads(latest.get('integrity_json') or '{}')
    except Exception:return {'status':'OBSERVE','reasons':['NEUTRALIZATION_METADATA_INVALID']}
    n=meta.get('neutralization') or {}
    reasons=[]
    if not n:reasons.append('NEUTRALIZATION_METADATA_MISSING')
    elif n.get('status') not in {'PASS','CAUTION'}:reasons.append('NEUTRALIZATION_NOT_VALID')
    if (n.get('diagnostics') or {}).get('max_neutral_abs_factor_corr',0)>.15:
        reasons.append('RESIDUAL_FACTOR_EXPOSURE')
    return {'status':'PASS' if not reasons else 'OBSERVE','reasons':reasons,'neutralization':n,
            'policy':'Promotion requires inspectable factor-neutralization evidence; sector metadata gaps remain explicit.'}
