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


def purged_walk_forward_lab(tickers=None,period='5y',limit=120,train_days=252,test_days=63,purge_days=5,embargo_days=5):
    """Rolling cross-sectional OOS validation with purge and embargo.
    Purge removes train observations whose forward label window can overlap the test boundary.
    Embargo skips dates immediately after each test block before the next training window.
    """
    ds=build_panel(tickers,period,limit)
    if ds.get('status')!='OK':return {k:v for k,v in ds.items() if k!='frame'}
    st=adapter_status()
    if not st.get('lightgbm_installed'):
        return {'status':'ADAPTER_UNAVAILABLE','symbols':ds['symbols'],'dates':ds['dates'],**st}
    df=ds['frame'].sort_values(['date','ticker']).copy()
    dates=sorted(df.date.unique())
    train_days=max(120,int(train_days));test_days=max(20,int(test_days));purge_days=max(5,int(purge_days));embargo_days=max(0,int(embargo_days))
    if len(dates)<train_days+test_days+purge_days+20:
        return {'status':'INSUFFICIENT_DATES','dates':len(dates),'required':train_days+test_days+purge_days+20}
    import lightgbm as lgb
    feats=ds['features'];folds=[];all_ics=[];all_spreads=[];cursor=train_days
    while cursor+purge_days+test_days<=len(dates):
        train_end=cursor-purge_days
        train_start=max(0,train_end-train_days)
        test_start=cursor
        test_end=min(len(dates),test_start+test_days)
        tr_dates=set(dates[train_start:train_end]);te_dates=set(dates[test_start:test_end])
        if len(tr_dates)<120 or len(te_dates)<20:break
        train=df[df.date.isin(tr_dates)]
        test=df[df.date.isin(te_dates)].copy()
        if train.empty or test.empty:break
        model=lgb.LGBMRegressor(n_estimators=120,max_depth=4,num_leaves=31,learning_rate=.03,
                                subsample=.8,colsample_bytree=.8,random_state=51,verbosity=-1)
        model.fit(train[feats],train['label_excess_5d'])
        test['prediction']=model.predict(test[feats])
        ics=[x for _,g in test.groupby('date') if (x:=_rank_ic(g)) is not None]
        spreads=[]
        for _,g in test.groupby('date'):
            if len(g)<10:continue
            z=g.sort_values('prediction');k=max(1,len(z)//10)
            spreads.append(float(z.tail(k)['label_excess_5d'].mean()-z.head(k)['label_excess_5d'].mean()))
        all_ics+=ics;all_spreads+=spreads
        folds.append({'fold':len(folds)+1,'train_start':dates[train_start],'train_end':dates[train_end-1],
                      'purged_dates':purge_days,'test_start':dates[test_start],'test_end':dates[test_end-1],
                      'train_dates':len(tr_dates),'test_dates':len(te_dates),
                      'mean_rank_ic':None if not ics else round(float(np.mean(ics)),4),
                      'positive_rank_ic_pct':None if not ics else round(float(np.mean(np.array(ics)>0)*100),1),
                      'mean_top_bottom_spread_5d':None if not spreads else round(float(np.mean(spreads)),5),
                      'positive_spread_pct':None if not spreads else round(float(np.mean(np.array(spreads)>0)*100),1)})
        cursor=test_end+embargo_days
    if not folds:return {'status':'NO_FOLDS','dates':len(dates)}
    return {'status':'LAB_RESULT','symbols':ds['symbols'],'dates':ds['dates'],'folds':folds,
            'fold_count':len(folds),'purge_days':purge_days,'embargo_days':embargo_days,
            'aggregate_mean_rank_ic':None if not all_ics else round(float(np.mean(all_ics)),4),
            'aggregate_median_rank_ic':None if not all_ics else round(float(np.median(all_ics)),4),
            'aggregate_positive_rank_ic_pct':None if not all_ics else round(float(np.mean(np.array(all_ics)>0)*100),1),
            'aggregate_mean_top_bottom_spread_5d':None if not all_spreads else round(float(np.mean(all_spreads)),5),
            'aggregate_positive_spread_pct':None if not all_spreads else round(float(np.mean(np.array(all_spreads)>0)*100),1),
            'note':'Purged/embargoed rolling OOS research validation. No production or order path is enabled.'}


def _basket_turnover(prev,current):
    prev=set(prev or []);current=set(current or [])
    if not prev and not current:return 0.0
    if not prev:return 1.0
    return 1.0-len(prev&current)/max(1,len(current))

def cost_turnover_reality_from_ranked(days,one_way_cost_bps=20,rebalance_every=5,portfolio_value=1_000_000,adv_limit_pct=1.0):
    """Turnover/cost/capacity diagnostics for ranked cross-sectional snapshots."""
    one_way=max(0,float(one_way_cost_bps));rebalance=max(1,int(rebalance_every));pv=max(1,float(portfolio_value));adv_lim=max(.1,min(float(adv_limit_pct),10))/100
    prev_top=[];gross=[];net=[];turns=[];cap_flags=0;rows=[]
    for i,d in enumerate(days or []):
        if i%rebalance!=0:continue
        z=sorted(d.get('rows') or [],key=lambda x:float(x.get('score') or -1e18))
        if len(z)<10:continue
        k=max(1,len(z)//10);low=z[:k];top=z[-k:]
        top_names=[x.get('ticker') for x in top];turn=_basket_turnover(prev_top,top_names);prev_top=top_names
        g=float(np.mean([float(x.get('label_excess_5d') or 0) for x in top])-np.mean([float(x.get('label_excess_5d') or 0) for x in low]))
        cost=(2*one_way/10000)*turn;n=g-cost
        gross.append(g);net.append(n);turns.append(turn)
        alloc=pv/max(1,k);caps=[]
        for x in top:
            adv=float(x.get('value_turnover') or 0)
            if adv<=0 or alloc>adv*adv_lim:caps.append(x.get('ticker'))
        if caps:cap_flags+=1
        rows.append({'date':d.get('date'),'basket_size':k,'turnover_pct':round(turn*100,1),
                     'gross_spread_5d':round(g,5),'cost_drag_5d':round(cost,5),'net_spread_5d':round(n,5),
                     'capacity_flags':caps[:20]})
    if not rows:return {'status':'NO_REBALANCES'}
    return {'status':'OK','rebalances':len(rows),'one_way_cost_bps':one_way,'rebalance_every':rebalance,
            'mean_turnover_pct':round(float(np.mean(turns))*100,1),
            'gross_mean_spread_5d':round(float(np.mean(gross)),5),
            'net_mean_spread_5d':round(float(np.mean(net)),5),
            'net_positive_pct':round(float(np.mean(np.array(net)>0)*100),1),
            'capacity_flagged_rebalances':cap_flags,'rows':rows[-50:],
            'policy':'Costs and capacity can only reduce or veto an edge; they never improve expected performance.'}
