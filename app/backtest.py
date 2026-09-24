from __future__ import annotations
import pandas as pd, numpy as np
from .market_data import yahoo_chart

def run_backtest(ticker, fast=20, slow=50, period='2y'):
    d=yahoo_chart(ticker,period=period,interval='1d'); rows=d.get('candles',[])
    if len(rows)<slow+5: return {'error':'insufficient_history'}
    df=pd.DataFrame(rows); c=df['close'].astype(float); f=c.rolling(fast).mean(); s=c.rolling(slow).mean()
    pos=(f>s).astype(float).shift(1).fillna(0); ret=c.pct_change().fillna(0); strat=pos*ret
    eq=(1+strat).cumprod(); bh=(1+ret).cumprod(); dd=eq/eq.cummax()-1
    trades=int((pos.diff().abs()>0).sum()); active=strat[pos>0]; wins=float((active>0).mean()*100) if len(active) else 0
    ann=np.sqrt(252)*strat.mean()/strat.std() if strat.std() else 0
    return {'ticker':ticker.upper(),'fast':fast,'slow':slow,'return_pct':round((eq.iloc[-1]-1)*100,2),
      'buy_hold_pct':round((bh.iloc[-1]-1)*100,2),'alpha_pct':round((eq.iloc[-1]-bh.iloc[-1])*100,2),
      'sharpe':round(float(ann),2),'max_drawdown':round(float(dd.min()*100),2),'win_rate':round(wins,1),
      'trades':trades,'equity':[{'time':rows[i]['time'],'value':round(float(eq.iloc[i]*100),2)} for i in range(len(rows))]}
