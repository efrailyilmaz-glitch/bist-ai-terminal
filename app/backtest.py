from __future__ import annotations
import math
import numpy as np
import pandas as pd
from .market_data import yahoo_rows
from .scoring import indicator_frame
from .advanced_indicators import add_supertrend

TRADING_DAYS=252

def _frame(ticker,period='5y'):
    d=yahoo_rows(ticker,period=period,interval='1d')
    rows=d.get('candles',[])
    if len(rows)<80:return None,rows
    df=pd.DataFrame(rows)
    df=df.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
    return df,rows

def _positions(df,strategy='ma_trend',fast=20,slow=50):
    x=indicator_frame(df)
    c=x['Close'].astype(float)
    strategy=(strategy or 'ma_trend').lower()
    if strategy=='ma_trend':
        f=c.ewm(span=fast,adjust=False).mean();s=c.ewm(span=slow,adjust=False).mean()
        pos=(f>s).astype(float)
    elif strategy=='momentum':
        look=max(10,fast);mom=c.pct_change(look)
        pos=(mom>0).astype(float)
    elif strategy=='breakout':
        look=max(20,slow)
        hi=c.shift(1).rolling(look).max()
        exit_ma=c.ewm(span=max(10,fast),adjust=False).mean()
        pos=pd.Series(0.0,index=c.index);on=False
        for i in range(len(c)):
            if pd.isna(hi.iloc[i]):continue
            if not on and c.iloc[i]>hi.iloc[i]:on=True
            elif on and c.iloc[i]<exit_ma.iloc[i]:on=False
            pos.iloc[i]=1.0 if on else 0.0
    elif strategy=='rsi_reversion':
        r=x['RSI14']
        pos=pd.Series(0.0,index=c.index);on=False
        for i in range(len(c)):
            rv=r.iloc[i]
            if pd.isna(rv):continue
            if not on and rv<30:on=True
            elif on and rv>55:on=False
            pos.iloc[i]=1.0 if on else 0.0
    elif strategy=='supertrend':
        st=add_supertrend(df,10,3.0)
        pos=st['SUPERTREND_BULL'].astype(float)
    else:
        raise ValueError('unknown_strategy')
    return pos.shift(1).fillna(0)

def _metrics(df,pos,cost_bps=10,slippage_bps=5):
    c=df['Close'].astype(float)
    ret=c.pct_change().fillna(0)
    changes=pos.diff().abs().fillna(pos.abs())
    costs=changes*(cost_bps+slippage_bps)/10000
    strat=pos*ret-costs
    eq=(1+strat).cumprod()
    bh=(1+ret).cumprod()
    dd=eq/eq.cummax()-1
    years=max(len(strat)/TRADING_DAYS,1/TRADING_DAYS)
    total=float(eq.iloc[-1]-1)
    cagr=(float(eq.iloc[-1])**(1/years)-1) if eq.iloc[-1]>0 else -1
    vol=float(strat.std()*math.sqrt(TRADING_DAYS))
    sharpe=float(strat.mean()/strat.std()*math.sqrt(TRADING_DAYS)) if strat.std()>0 else 0
    downside=strat[strat<0].std()
    sortino=float(strat.mean()/downside*math.sqrt(TRADING_DAYS)) if downside and downside>0 else 0
    maxdd=float(dd.min())
    calmar=float(cagr/abs(maxdd)) if maxdd<0 else 0
    trades=int((changes>0).sum())
    active=strat[pos>0]
    win=float((active>0).mean()*100) if len(active) else 0
    gains=float(active[active>0].sum());loss=abs(float(active[active<0].sum()))
    pf=gains/loss if loss>0 else (999 if gains>0 else 0)
    exposure=float(pos.mean()*100)
    var95=float(np.quantile(strat,0.05)*100) if len(strat)>20 else 0
    cvar95=float(strat[strat<=np.quantile(strat,0.05)].mean()*100) if len(strat)>20 else 0
    return {
      'return_pct':round(total*100,2),'buy_hold_pct':round((bh.iloc[-1]-1)*100,2),
      'alpha_pct':round((eq.iloc[-1]-bh.iloc[-1])*100,2),'cagr_pct':round(cagr*100,2),
      'annual_volatility_pct':round(vol*100,2),'sharpe':round(sharpe,2),'sortino':round(sortino,2),
      'max_drawdown':round(maxdd*100,2),'calmar':round(calmar,2),'win_rate':round(win,1),
      'profit_factor':round(min(pf,999),2),'trades':trades,'exposure_pct':round(exposure,1),
      'var95_daily_pct':round(var95,2),'cvar95_daily_pct':round(cvar95,2),
      'equity_values':eq,'strategy_returns':strat,'buy_hold_values':bh
    }

def run_backtest(ticker,fast=20,slow=50,period='5y',strategy='ma_trend',cost_bps=10,slippage_bps=5):
    df,rows=_frame(ticker,period)
    if df is None or len(df)<max(slow+5,80):return {'error':'insufficient_history'}
    pos=_positions(df,strategy,fast,slow)
    m=_metrics(df,pos,cost_bps,slippage_bps)
    eq=m.pop('equity_values');m.pop('strategy_returns');bh=m.pop('buy_hold_values')
    m.update({'ticker':ticker.upper(),'strategy':strategy,'fast':fast,'slow':slow,'period':period,
              'cost_bps':cost_bps,'slippage_bps':slippage_bps,
              'equity':[{'time':rows[i]['time'],'value':round(float(eq.iloc[i]*100),2),'buy_hold':round(float(bh.iloc[i]*100),2)} for i in range(len(rows))]})
    return m

def compare_strategies(ticker,period='5y',cost_bps=10,slippage_bps=5):
    specs=[('ma_trend',20,50),('momentum',20,50),('breakout',20,55),('rsi_reversion',20,50),('supertrend',20,50)]
    rows=[]
    for name,fast,slow in specs:
        r=run_backtest(ticker,fast,slow,period,name,cost_bps,slippage_bps)
        if 'error' not in r:
            rows.append({k:v for k,v in r.items() if k!='equity'})
    return {'ticker':ticker.upper(),'period':period,'rows':rows}

def walk_forward(ticker,period='5y',strategy='ma_trend',cost_bps=10,slippage_bps=5):
    df,rows=_frame(ticker,period)
    if df is None or len(df)<420:return {'error':'insufficient_history_for_walk_forward'}
    grid=[(10,30),(15,40),(20,50),(30,75),(50,100)]
    train=252;test=63;cursor=train;segments=[]
    combined=[];combined_dates=[]
    while cursor+test<=len(df):
        tr=df.iloc[cursor-train:cursor].copy();te=df.iloc[cursor:cursor+test].copy()
        scored=[]
        for fast,slow in grid:
            try:
                p=_positions(tr,strategy,fast,slow);m=_metrics(tr,p,cost_bps,slippage_bps)
                scored.append((m['sharpe'],m['return_pct'],fast,slow))
            except Exception:pass
        if not scored:break
        _,_,fast,slow=max(scored)
        context=df.iloc[max(0,cursor-slow-20):cursor+test].copy()
        p=_positions(context,strategy,fast,slow)
        ptest=p.iloc[-test:]
        m=_metrics(te.reset_index(drop=True),ptest.reset_index(drop=True),cost_bps,slippage_bps)
        combined.extend((m['strategy_returns']).tolist())
        combined_dates.extend(rows[cursor:cursor+test])
        segments.append({'start':rows[cursor]['time'],'end':rows[cursor+test-1]['time'],'fast':fast,'slow':slow,
                         'return_pct':m['return_pct'],'sharpe':m['sharpe'],'max_drawdown':m['max_drawdown']})
        cursor+=test
    if not combined:return {'error':'walk_forward_failed'}
    sr=pd.Series(combined).fillna(0);eq=(1+sr).cumprod();dd=eq/eq.cummax()-1
    sharpe=float(sr.mean()/sr.std()*math.sqrt(TRADING_DAYS)) if sr.std()>0 else 0
    return {'ticker':ticker.upper(),'strategy':strategy,'segments':segments,'oos_return_pct':round((eq.iloc[-1]-1)*100,2),
            'oos_sharpe':round(sharpe,2),'oos_max_drawdown_pct':round(float(dd.min()*100),2),
            'equity':[{'time':combined_dates[i]['time'],'value':round(float(eq.iloc[i]*100),2)} for i in range(len(eq))]}

def monte_carlo(ticker,period='5y',strategy='ma_trend',fast=20,slow=50,cost_bps=10,slippage_bps=5,simulations=500,horizon=252,seed=42):
    df,_=_frame(ticker,period)
    if df is None:return {'error':'insufficient_history'}
    pos=_positions(df,strategy,fast,slow)
    m=_metrics(df,pos,cost_bps,slippage_bps)
    r=m['strategy_returns'].dropna().values
    if len(r)<80:return {'error':'insufficient_returns'}
    rng=np.random.default_rng(seed);finals=[];maxdds=[]
    block=5
    for _ in range(max(100,min(simulations,2000))):
        seq=[]
        while len(seq)<horizon:
            j=int(rng.integers(0,max(1,len(r)-block)))
            seq.extend(r[j:j+block].tolist())
        seq=np.array(seq[:horizon])
        eq=np.cumprod(1+seq);dd=eq/np.maximum.accumulate(eq)-1
        finals.append((eq[-1]-1)*100);maxdds.append(dd.min()*100)
    return {'ticker':ticker.upper(),'strategy':strategy,'simulations':len(finals),'horizon_days':horizon,
            'return_p10':round(float(np.quantile(finals,.10)),2),'return_median':round(float(np.median(finals)),2),
            'return_p90':round(float(np.quantile(finals,.90)),2),'maxdd_median':round(float(np.median(maxdds)),2),
            'maxdd_p10':round(float(np.quantile(maxdds,.10)),2),
            'prob_positive_pct':round(float(np.mean(np.array(finals)>0)*100),1),
            'note':'Block-bootstrap of historical strategy returns; distribution, not a forecast.'}
