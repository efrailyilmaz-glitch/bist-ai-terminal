"""V107 capacity and market-impact scale analysis.
Tests the same ticker across multiple notional sizes using current observable liquidity/volatility.
Research/paper diagnostics only; capacity can only reduce exposure.
"""
from __future__ import annotations
import math
from .market_data import scan_codes,daily_frames
from .xs_capacity import assess

DEFAULT_SCALES=[100_000,250_000,500_000,1_000_000,2_500_000,5_000_000,10_000_000]

def _last(df,key):
    try:return float(df[key].dropna().iloc[-1])
    except Exception:return None

def analyze(ticker,scales=None,adv_limit_pct=1.0):
    code=str(ticker).upper().replace('.IS','')
    row=(scan_codes([code]) or [{}])[0]
    adv=float(row.get('avg_value_turnover_20') or 0)
    vol=float(row.get('volatility') or row.get('annual_volatility_pct') or 0)
    frames=daily_frames([code]);df=frames.get(code)
    px=_last(df,'Close');hi=_last(df,'High');lo=_last(df,'Low')
    vals=[max(0,float(x)) for x in (scales or DEFAULT_SCALES) if float(x)>0]
    out=[]
    for n in vals:
        r=assess(n,0,adv,vol,price=px,high=hi,low=lo,adv_limit_pct=adv_limit_pct,max_horizon_days=2)
        out.append({'notional':round(n,2),**r})
    clear=[x for x in out if x.get('status')=='CLEAR'];caution=[x for x in out if x.get('status')=='CAUTION']
    max_clear=max((x['notional'] for x in clear),default=0)
    max_non_block=max((x['notional'] for x in clear+caution),default=0)
    first_block=next((x for x in out if x.get('status')=='BLOCK'),None)
    return {'status':'OK','version':'107.0','ticker':code,'price':px,'adv_value':round(adv,2),'annual_volatility_pct':vol,
            'adv_limit_pct':float(adv_limit_pct),'rows':out,'max_clear_notional':round(max_clear,2),
            'max_non_block_notional':round(max_non_block,2),'first_block_notional':None if not first_block else first_block['notional'],
            'live_execution':False,
            'policy':'Scale test is a paper/research capacity diagnostic. Larger capital can only worsen or preserve execution assumptions; it never boosts expected returns.'}

def portfolio(codes,portfolio_values=None,target_weight_pct=10.0,adv_limit_pct=1.0):
    codes=list(dict.fromkeys(str(x).upper().replace('.IS','') for x in codes if x))[:20]
    pvs=[float(x) for x in (portfolio_values or [1_000_000,2_500_000,5_000_000,10_000_000,25_000_000])]
    rows=[]
    for pv in pvs:
        blocked=caution=0;worst_impact=0;max_horizon=0;details=[]
        target=pv*max(0,min(float(target_weight_pct),50))/100
        for code in codes:
            a=analyze(code,[target],adv_limit_pct);r=(a.get('rows') or [{}])[0]
            blocked+=int(r.get('status')=='BLOCK');caution+=int(r.get('status') in {'CAUTION','UNKNOWN'})
            worst_impact=max(worst_impact,float(r.get('effective_impact_bps') or 0))
            max_horizon=max(max_horizon,int(r.get('execution_horizon_days') or 0))
            details.append({'ticker':code,'target_notional':round(target,2),'status':r.get('status'),'impact_bps':r.get('effective_impact_bps'),'horizon_days':r.get('execution_horizon_days')})
        status='BLOCK' if blocked else 'CAUTION' if caution else 'CLEAR'
        rows.append({'portfolio_value':round(pv,2),'target_weight_pct':float(target_weight_pct),'status':status,'blocked_names':blocked,'caution_names':caution,'worst_impact_bps':round(worst_impact,2),'max_horizon_days':max_horizon,'details':details})
    return {'status':'OK','version':'107.0','tickers':codes,'rows':rows,'live_execution':False,
            'policy':'Portfolio capacity scale test assumes the same target weight per name and observable ADV. It is conservative research, not a promise of fill quality.'}
