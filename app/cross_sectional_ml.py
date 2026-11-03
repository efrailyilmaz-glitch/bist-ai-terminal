"""V50 cross-sectional ML challenger.
Ranks BIST names against each other on the same date using causal features.
Lab-only: no paper/live order path and no production score mutation.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from .qlib_bridge import feature_frame, FEATURES, adapter_status
from .universe import get_universe

def _rank_ic(g):
    if len(g)<5:return None
    p=g['prediction'].rank(pct=True)
    y=g['label_excess_5d'].rank(pct=True)
    if p.std()==0 or y.std()==0:return 0.0
    return float(p.corr(y))

def build_panel(tickers=None,period='5y',limit=120):
    names=tickers or [x['ticker'] for x in get_universe()[:max(5,min(limit,500))]]
    frames=[]
    failed=[]
    for t in names:
        try:
            f=feature_frame(t,period)
            if f.empty:failed.append(t);continue
            x=f.copy();x['ticker']=t;x['date']=x.index.astype(str)
            frames.append(x.reset_index(drop=True))
        except Exception:
            failed.append(t)
    if not frames:return {'status':'NO_DATA','frame':pd.DataFrame(),'requested':len(names),'failed':failed}
    panel=pd.concat(frames,ignore_index=True)
    panel=panel.dropna(subset=FEATURES+['label_5d'])
    # Cross-sectional target: forward return minus same-date universe mean.
    means=panel.groupby('date')['label_5d'].transform('mean')
    panel['label_excess_5d']=panel['label_5d']-means
    # Date-wise z-scoring prevents absolute scale drift and focuses on relative ranking.
    for c in FEATURES:
        mu=panel.groupby('date')[c].transform('mean')
        sd=panel.groupby('date')[c].transform('std').replace(0,np.nan)
        panel['xs_'+c]=(panel[c]-mu)/sd
    xs_features=['xs_'+c for c in FEATURES]
    panel=panel.dropna(subset=xs_features+['label_excess_5d'])
    return {'status':'OK' if len(panel) else 'INSUFFICIENT_DATA','frame':panel,
            'requested':len(names),'symbols':int(panel.ticker.nunique()) if len(panel) else 0,
            'dates':int(panel.date.nunique()) if len(panel) else 0,'failed':failed[:50],
            'features':xs_features,'label':'label_excess_5d'}

def run_lab(tickers=None,period='5y',limit=120,train_ratio=.7):
    ds=build_panel(tickers,period,limit)
    if ds.get('status')!='OK':return {k:v for k,v in ds.items() if k!='frame'}
    st=adapter_status()
    if not st.get('lightgbm_installed'):
        return {'status':'ADAPTER_UNAVAILABLE','symbols':ds['symbols'],'dates':ds['dates'],**st}
    import lightgbm as lgb
    df=ds['frame'].sort_values(['date','ticker']).copy()
    dates=sorted(df.date.unique())
    if len(dates)<180:return {'status':'INSUFFICIENT_DATES','dates':len(dates),'symbols':ds['symbols']}
    cut=max(120,min(len(dates)-40,int(len(dates)*train_ratio)))
    train_dates=set(dates[:cut]);test_dates=set(dates[cut:])
    train=df[df.date.isin(train_dates)];test=df[df.date.isin(test_dates)].copy()
    feats=ds['features']
    model=lgb.LGBMRegressor(n_estimators=120,max_depth=4,num_leaves=31,learning_rate=.03,
                            subsample=.8,colsample_bytree=.8,random_state=50,verbosity=-1)
    model.fit(train[feats],train['label_excess_5d'])
    test['prediction']=model.predict(test[feats])
    ics=[x for _,g in test.groupby('date') if (x:=_rank_ic(g)) is not None]
    spreads=[];rows=[]
    for d,g in test.groupby('date'):
        if len(g)<10:continue
        g=g.sort_values('prediction')
        k=max(1,len(g)//10)
        bottom=g.head(k);top=g.tail(k)
        spread=float(top['label_excess_5d'].mean()-bottom['label_excess_5d'].mean())
        spreads.append(spread)
        if len(rows)<60:
            rows.append({'date':d,'universe':len(g),'top_mean_excess_5d':round(float(top['label_excess_5d'].mean()),5),
                         'bottom_mean_excess_5d':round(float(bottom['label_excess_5d'].mean()),5),
                         'top_bottom_spread':round(spread,5)})
    latest=test[test.date==test.date.max()].sort_values('prediction',ascending=False)
    latest_rows=[{'ticker':r.ticker,'score':round(float(r.prediction),6),'label_excess_5d':round(float(r.label_excess_5d),6)}
                 for r in latest.head(20).itertuples()]
    return {'status':'LAB_RESULT','symbols':ds['symbols'],'dates':ds['dates'],'train_dates':len(train_dates),'test_dates':len(test_dates),
            'oos_mean_rank_ic':None if not ics else round(float(np.mean(ics)),4),
            'oos_median_rank_ic':None if not ics else round(float(np.median(ics)),4),
            'oos_positive_rank_ic_pct':None if not ics else round(float(np.mean(np.array(ics)>0)*100),1),
            'oos_mean_top_bottom_spread_5d':None if not spreads else round(float(np.mean(spreads)),5),
            'oos_positive_spread_pct':None if not spreads else round(float(np.mean(np.array(spreads)>0)*100),1),
            'latest_ranked':latest_rows,'daily_spreads':rows[-30:],
            'model_card':{'name':'BIST Cross-Sectional LightGBM Challenger','version':'50.0','source':'BIST AI lab',
                          'input_schema':feats,'output_schema':['relative_5d_excess_score'],'point_in_time':True,
                          'execution_compatible':False},
            'note':'Research-only cross-sectional OOS ranking. No production or order path is enabled.'}
