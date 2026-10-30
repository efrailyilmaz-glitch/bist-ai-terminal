"""Robustness diagnostics for strategy research.
Designed to reject fragile backtests, not to certify profitability.
"""
from __future__ import annotations
import itertools, math
import numpy as np
import pandas as pd
from .backtest import _frame,_positions,_metrics,TRADING_DAYS

CANDIDATES=[
 ('ma_trend',10,30),('ma_trend',20,50),('ma_trend',30,75),
 ('momentum',20,50),('momentum',60,100),('momentum',120,200),
 ('breakout',20,40),('breakout',20,55),('breakout',30,75),
 ('rsi_reversion',10,30),('rsi_reversion',20,50),
 ('supertrend',20,50)
]

def _sharpe(r):
    s=pd.Series(r,dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    if len(s)<10 or float(s.std())<=0:return 0.0
    return float(s.mean()/s.std()*math.sqrt(TRADING_DAYS))

def candidate_returns(df,cost_bps=10,slippage_bps=5):
    cols={};meta=[]
    for i,(strategy,fast,slow) in enumerate(CANDIDATES):
        try:
            pos=_positions(df,strategy,fast,slow)
            m=_metrics(df,pos,cost_bps,slippage_bps)
            r=pd.Series(m['strategy_returns'],index=df.index,dtype=float).fillna(0)
            key=f'{strategy}:{fast}:{slow}'
            cols[key]=r;meta.append({'id':key,'strategy':strategy,'fast':fast,'slow':slow})
        except Exception:
            continue
    return pd.DataFrame(cols,index=df.index).fillna(0),meta

def pbo_cscv(returns,slices=8):
    """Approximate Bailey et al. CSCV PBO using equal contiguous blocks."""
    r=pd.DataFrame(returns).replace([np.inf,-np.inf],np.nan).fillna(0)
    n=len(r);m=r.shape[1]
    if n<240 or m<3:return {'status':'INSUFFICIENT_DATA'}
    slices=max(6,min(int(slices),10))
    if slices%2:slices-=1
    blocks=[x for x in np.array_split(np.arange(n),slices) if len(x)]
    half=len(blocks)//2;lambdas=[];oos_percentiles=[]
    for choice in itertools.combinations(range(len(blocks)),half):
        inside=set(choice)
        is_idx=np.concatenate([blocks[i] for i in range(len(blocks)) if i in inside])
        oos_idx=np.concatenate([blocks[i] for i in range(len(blocks)) if i not in inside])
        is_scores=np.array([_sharpe(r.iloc[is_idx,j]) for j in range(m)])
        best=int(np.argmax(is_scores))
        oos_scores=np.array([_sharpe(r.iloc[oos_idx,j]) for j in range(m)])
        # percentile of selected strategy, 0=worst, 1=best
        rank=float((oos_scores<oos_scores[best]).sum()+0.5*(oos_scores==oos_scores[best]).sum())/m
        rank=min(.999999,max(.000001,rank));oos_percentiles.append(rank)
        lambdas.append(math.log(rank/(1-rank)))
    pbo=float(np.mean(np.array(lambdas)<0)) if lambdas else 1.0
    return {'status':'OK','slices':len(blocks),'combinations':len(lambdas),
            'pbo_pct':round(pbo*100,1),'median_selected_oos_percentile':round(float(np.median(oos_percentiles))*100,1),
            'interpretation':'Lower PBO is better. This is a candidate-family diagnostic, not proof of future alpha.'}

def walk_forward_surface(returns,train=252,test=63):
    """Correlation between the full IS and OOS candidate performance surfaces."""
    r=pd.DataFrame(returns).replace([np.inf,-np.inf],np.nan).fillna(0)
    if len(r)<train+test or r.shape[1]<3:return {'status':'INSUFFICIENT_DATA'}
    rows=[];cursor=train
    while cursor+test<=len(r):
        is_scores=np.array([_sharpe(r.iloc[cursor-train:cursor,j]) for j in range(r.shape[1])])
        os_scores=np.array([_sharpe(r.iloc[cursor:cursor+test,j]) for j in range(r.shape[1])])
        if np.std(is_scores)>1e-9 and np.std(os_scores)>1e-9:
            corr=float(np.corrcoef(is_scores,os_scores)[0,1])
        else:corr=0.0
        best=int(np.argmax(is_scores))
        rows.append({'train_start':int(cursor-train),'test_start':int(cursor),
                     'surface_corr':round(corr,3),'selected_oos_sharpe':round(float(os_scores[best]),3),
                     'selected_oos_positive':bool(os_scores[best]>0)})
        cursor+=test
    if not rows:return {'status':'INSUFFICIENT_DATA'}
    corrs=[x['surface_corr'] for x in rows];positive=np.mean([x['selected_oos_positive'] for x in rows])*100
    return {'status':'OK','folds':len(rows),'median_surface_corr':round(float(np.median(corrs)),3),
            'mean_surface_corr':round(float(np.mean(corrs)),3),'positive_selected_oos_folds_pct':round(float(positive),1),
            'fold_rows':rows,
            'interpretation':'Positive IS→OOS surface correlation suggests parameter neighborhoods transfer better than an isolated optimum.'}

def stability_map(returns):
    r=pd.DataFrame(returns).fillna(0)
    full=np.array([_sharpe(r.iloc[:,j]) for j in range(r.shape[1])])
    if not len(full):return {'status':'NO_DATA'}
    order=np.argsort(full)[::-1];best=float(full[order[0]])
    near=[int(i) for i in order if full[i]>=best-.25]
    return {'status':'OK','best_sharpe':round(best,3),'near_best_count':len(near),'candidate_count':len(full),
            'plateau_pct':round(len(near)/len(full)*100,1),
            'best_index':int(order[0]),
            'note':'A broader near-best plateau is preferred to a single sharp optimum.'}

def robustness_audit(ticker,period='10y',cost_bps=15,slippage_bps=10):
    df,_=_frame(ticker,period)
    if df is None or len(df)<500:return {'ticker':ticker.upper(),'status':'INSUFFICIENT_HISTORY'}
    returns,meta=candidate_returns(df,cost_bps,slippage_bps)
    if returns.shape[1]<3:return {'ticker':ticker.upper(),'status':'NO_CANDIDATES'}
    pbo=pbo_cscv(returns);wfc=walk_forward_surface(returns);plateau=stability_map(returns)
    stress2,_=candidate_returns(df,cost_bps*2,slippage_bps*2);stress3,_=candidate_returns(df,cost_bps*3,slippage_bps*3)
    full_scores=[_sharpe(returns.iloc[:,j]) for j in range(returns.shape[1])]
    stress2_scores=[_sharpe(stress2.iloc[:,j]) for j in range(stress2.shape[1])] if not stress2.empty else []
    stress3_scores=[_sharpe(stress3.iloc[:,j]) for j in range(stress3.shape[1])] if not stress3.empty else []
    best=int(np.argmax(full_scores));best_meta=meta[best]
    # Deliberately conservative research gate. It authorizes only prospective paper validation.
    reasons=[]
    if pbo.get('pbo_pct',100)>25:reasons.append('PBO_HIGH')
    if wfc.get('median_surface_corr',-1)<.15:reasons.append('LOW_IS_OOS_SURFACE_CORRELATION')
    if wfc.get('positive_selected_oos_folds_pct',0)<60:reasons.append('OOS_FOLD_MAJORITY_FAIL')
    if plateau.get('plateau_pct',0)<15:reasons.append('PARAMETER_CLIFF_RISK')
    if not stress2_scores or max(stress2_scores)<=0:reasons.append('DOUBLE_COST_EDGE_LOST')
    gate='PROSPECTIVE_PAPER' if not reasons else 'RESEARCH_ONLY'
    return {'ticker':ticker.upper(),'status':'OK','period':period,'cost_bps':cost_bps,'slippage_bps':slippage_bps,
            'candidate_count':returns.shape[1],'best_full_sample':{**best_meta,'sharpe':round(full_scores[best],3)},
            'pbo':pbo,'walk_forward_surface':wfc,'stability':plateau,
            'cost_stress':{'base_best_sharpe':round(max(full_scores),3),'double_cost_best_sharpe':round(max(stress2_scores),3) if stress2_scores else None,'triple_cost_best_sharpe':round(max(stress3_scores),3) if stress3_scores else None},
            'gate':gate,'veto_reasons':reasons,
            'limits':'Passing this gate never authorizes live trading. It only means the candidate family is eligible for locked prospective paper testing.'}
