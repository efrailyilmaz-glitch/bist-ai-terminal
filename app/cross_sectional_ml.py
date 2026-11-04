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
from .data_quality_guard import audit_current_snapshot, audit_training_panel, survivorship_guard
from .pit_universe import training_universe, filter_frame
from .factor_neutralization import neutralize as neutralize_scores

def _rank_ic(g):
    if len(g)<5:return None
    p=g['prediction'].rank(pct=True)
    y=g['label_excess_5d'].rank(pct=True)
    if p.std()==0 or y.std()==0:return 0.0
    return float(p.corr(y))

def build_panel(tickers=None,period='5y',limit=120):
    current=[x['ticker'] for x in get_universe()[:max(5,min(limit,500))]]
    resolved=training_universe(tickers if tickers is not None else current,limit)
    names=list(tickers)[:max(5,min(limit,500))] if tickers is not None else resolved['tickers']
    universe_integrity=resolved['integrity'] if tickers is None else {'status':'CAUTION','flags':['EXPLICIT_TICKER_SET_NOT_HISTORICAL_UNIVERSE'],
        'historical_universe_point_in_time':False,'current_universe_proxy':True,'survivorship_bias_risk':True}
    frames=[]
    failed=[]
    for t in names:
        try:
            f=feature_frame(t,period)
            if f.empty:failed.append(t);continue
            f=filter_frame(t,f,universe_integrity)
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
            'features':xs_features,'label':'label_excess_5d','universe_integrity':universe_integrity}

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


def purged_walk_forward_cost_reality(tickers=None,period='5y',limit=120,train_days=252,test_days=63,purge_days=5,embargo_days=5,one_way_cost_bps=20,rebalance_every=5,portfolio_value=1_000_000,adv_limit_pct=1.0):
    """Purged rolling validation plus implementation-cost and capacity diagnostics."""
    ds=build_panel(tickers,period,limit)
    if ds.get('status')!='OK':return {k:v for k,v in ds.items() if k!='frame'}
    st=adapter_status()
    if not st.get('lightgbm_installed'):
        return {'status':'ADAPTER_UNAVAILABLE','symbols':ds['symbols'],'dates':ds['dates'],**st}
    import lightgbm as lgb
    df=ds['frame'].sort_values(['date','ticker']).copy();dates=sorted(df.date.unique())
    train_days=max(120,int(train_days));test_days=max(20,int(test_days));purge_days=max(5,int(purge_days));embargo_days=max(0,int(embargo_days))
    if len(dates)<train_days+test_days+purge_days+20:
        return {'status':'INSUFFICIENT_DATES','dates':len(dates),'required':train_days+test_days+purge_days+20}
    feats=ds['features'];cursor=train_days;ranked_days=[]
    while cursor+purge_days+test_days<=len(dates):
        train_end=cursor-purge_days;train_start=max(0,train_end-train_days);test_start=cursor;test_end=min(len(dates),test_start+test_days)
        tr_dates=set(dates[train_start:train_end]);te_dates=set(dates[test_start:test_end])
        train=df[df.date.isin(tr_dates)];test=df[df.date.isin(te_dates)].copy()
        if train.empty or test.empty:break
        model=lgb.LGBMRegressor(n_estimators=120,max_depth=4,num_leaves=31,learning_rate=.03,
                                subsample=.8,colsample_bytree=.8,random_state=52,verbosity=-1)
        model.fit(train[feats],train['label_excess_5d']);test['prediction']=model.predict(test[feats])
        for d,g in test.groupby('date'):
            rows=[]
            for r in g.itertuples():
                rows.append({'ticker':r.ticker,'score':float(r.prediction),'label_excess_5d':float(r.label_excess_5d),
                             'value_turnover':float(getattr(r,'value_turnover',0) or 0)})
            ranked_days.append({'date':d,'rows':rows})
        cursor=test_end+embargo_days
    reality=cost_turnover_reality_from_ranked(ranked_days,one_way_cost_bps,rebalance_every,portfolio_value,adv_limit_pct)
    reality.update({'symbols':ds['symbols'],'dates':ds['dates'],'purge_days':purge_days,'embargo_days':embargo_days,
                    'note':'Purged rolling OOS implementation reality. Net edge must survive costs and capacity checks before promotion review.'})
    return reality


def current_ranking(tickers=None,period='5y',limit=120):
    """Train only on label-complete historical rows, then score the latest causal feature row.
    Prospective research ranking only. Requires optional LightGBM adapter.
    """
    st=adapter_status()
    if not st.get('lightgbm_installed'):
        return {'status':'ADAPTER_UNAVAILABLE',**st}
    names=tickers or [x['ticker'] for x in get_universe()[:max(5,min(limit,500))]]
    ds=build_panel(tickers,period,limit)
    if ds.get('status')!='OK':return {k:v for k,v in ds.items() if k!='frame'}
    train_quality=audit_training_panel(ds)
    if train_quality.get('status')=='BLOCK':
        return {'status':'DATA_QUALITY_BLOCK','training_quality':train_quality,
                'universe_integrity':ds.get('universe_integrity') or survivorship_guard(False,True)}
    latest=[]
    for t in names:
        try:
            f=feature_frame(t,period)
            if f.empty:continue
            r=f.iloc[-1]
            if any(pd.isna(r.get(k)) for k in FEATURES):continue
            latest.append({'ticker':t,'date':str(f.index[-1]),**{k:float(r[k]) for k in FEATURES},
                           'price':float(r.get('price') or 0),'value_turnover':float(r.get('value_turnover') or 0)})
        except Exception:continue
    if len(latest)<10:return {'status':'INSUFFICIENT_CURRENT_UNIVERSE','symbols':len(latest)}
    current_quality=audit_current_snapshot(latest,requested=len(names))
    if current_quality.get('status')=='BLOCK':
        return {'status':'DATA_QUALITY_BLOCK','symbols':len(latest),'current_quality':current_quality,
                'training_quality':train_quality,'universe_integrity':ds.get('universe_integrity') or survivorship_guard(False,True)}
    cur=pd.DataFrame(latest)
    for k in FEATURES:
        sd=float(cur[k].std())
        cur['xs_'+k]=(cur[k]-float(cur[k].mean()))/(sd if sd>0 else 1.0)
    feats=ds['features'];train=ds['frame'].sort_values(['date','ticker'])
    # Five-day labels require a conservative five-date gap before current scoring.
    td=sorted(train.date.unique())
    if len(td)>5:train=train[train.date.isin(set(td[:-5]))]
    if len(train)<500:return {'status':'INSUFFICIENT_TRAINING_ROWS','rows':len(train)}
    import lightgbm as lgb
    model=lgb.LGBMRegressor(n_estimators=120,max_depth=4,num_leaves=31,learning_rate=.03,
                            subsample=.8,colsample_bytree=.8,random_state=56,verbosity=-1)
    model.fit(train[feats],train['label_excess_5d'])
    cur['raw_score']=model.predict(cur[feats])
    meta={x['ticker']:{'sector':x.get('sector') or ((x.get('sectors') or [None])[0] if isinstance(x.get('sectors'),list) else None)} for x in get_universe()}
    cur['sector']=[(meta.get(t) or {}).get('sector') for t in cur['ticker']]
    neutral=neutralize_scores(cur,'raw_score','sector')
    if neutral.get('status') not in {'PASS','CAUTION'}:
        return {'status':'NEUTRALIZATION_BLOCK','neutralization':{k:v for k,v in neutral.items() if k!='frame'},
                'universe_integrity':ds.get('universe_integrity')}
    cur=neutral['frame'].sort_values('score',ascending=False)
    rows=[{'ticker':r.ticker,'score':round(float(r.score),6),'raw_score':round(float(r.raw_score),6),
           'price':round(float(r.price),6),'value_turnover':round(float(r.value_turnover),2),'as_of':str(r.date)}
          for r in cur.itertuples()]
    from .model_registry import register as register_model_artifact
    artifact=register_model_artifact({'model_name':'BIST Cross-Sectional LightGBM','model_version':'57.0','seed':56,
        'features':feats,'label':'label_excess_5d','train_rows':len(train),'train_dates':int(train.date.nunique()),
        'train_cutoff':str(max(train.date)) if len(train) else None,'as_of':str(cur.iloc[0]['date']),'symbols':len(rows),
        'universe_integrity':ds.get('universe_integrity'),
        'params':{'n_estimators':120,'max_depth':4,'num_leaves':31,'learning_rate':.03,'subsample':.8,'colsample_bytree':.8,
                  'neutralization':'V65_FACTORS_SECTOR_IF_AVAILABLE'}})
    return {'status':'OK','as_of':str(cur.iloc[0]['date']),'symbols':len(rows),'rows':rows,
            'train_rows':len(train),'model_artifact':artifact,
            'current_quality':current_quality,'training_quality':train_quality,
            'universe_integrity':ds.get('universe_integrity') or survivorship_guard(False,True),
            'neutralization':{k:v for k,v in neutral.items() if k!='frame'},
            'policy':'Latest features are causal; training excludes the most recent five labeled dates. Prospective paper use only.'}
