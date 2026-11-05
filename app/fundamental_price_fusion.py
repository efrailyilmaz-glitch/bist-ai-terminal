"""V110 Fundamental + Price Action Fusion.
Separates business quality/valuation from entry timing so a strong chart cannot hide weak fundamentals
and a strong company is not automatically treated as a good entry.
"""
from __future__ import annotations
from .fundamentals import get_fundamentals
from .premium_engine import fair_value_health
from .pro_tools import technical_pro,forensic_models
from .market_data import scan_codes

def analyze(ticker):
    code=str(ticker).upper().replace('.IS','')
    row=(scan_codes([code]) or [{}])[0]
    if not row:return {'ticker':code,'status':'NO_DATA'}
    fund=get_fundamentals(code);premium=fair_value_health(code);tech=technical_pro(code);forensic=forensic_models(code)
    fs=float(fund.get('fundamental_score') or 50)
    health=premium.get('health_score');health=50.0 if health is None else float(health)
    fv=premium.get('fair_value_upside_pct');fv=0.0 if fv is None else float(fv)
    piot=(premium.get('piotroski') or {}).get('score');alt=(premium.get('altman') or {}).get('status')
    beneish=(forensic.get('beneish') or {}).get('status')
    quality=max(0,min(100,.50*fs+.35*health+.15*max(0,min(100,50+fv))))
    timing=float(tech.get('alignment_score') or 50)
    if row.get('supertrend')=='BULLISH':timing+=8
    if row.get('ichimoku')=='BULLISH':timing+=8
    if row.get('above_ema200'):timing+=6
    if float(row.get('risk') or 50)>=75:timing-=15
    timing=max(0,min(100,timing))
    hard_fundamental_risk=(alt=='DISTRESS' or beneish=='ELEVATED_RISK')
    if hard_fundamental_risk:
        state='FUNDAMENTAL_RISK_OVERRIDE'
    elif quality>=68 and timing>=68:
        state='QUALITY_AND_TIMING_ALIGNED'
    elif quality>=68 and timing<55:
        state='GOOD_COMPANY_BAD_ENTRY'
    elif quality<48 and timing>=68:
        state='STRONG_CHART_WEAK_FUNDAMENTALS'
    elif quality>=55 and timing>=55:
        state='MIXED_POSITIVE'
    else:
        state='WEAK_OR_UNCONFIRMED'
    action='RESEARCH_CANDIDATE' if state=='QUALITY_AND_TIMING_ALIGNED' else 'WAIT_FOR_ENTRY' if state=='GOOD_COMPANY_BAD_ENTRY' else 'AVOID_CHASING' if state in {'STRONG_CHART_WEAK_FUNDAMENTALS','FUNDAMENTAL_RISK_OVERRIDE'} else 'MONITOR'
    return {'ticker':code,'status':'OK','version':'110.0','state':state,'research_action':action,
            'fundamental_quality_score':round(quality,1),'price_action_timing_score':round(timing,1),
            'fundamental_score':round(fs,1),'health_score':round(health,1),'fair_value_upside_pct':round(fv,2),
            'piotroski':piot,'altman':alt,'beneish':beneish,'technical_alignment':tech.get('alignment_score'),
            'supertrend':row.get('supertrend'),'ichimoku':row.get('ichimoku'),'above_ema200':row.get('above_ema200'),
            'hard_fundamental_risk':hard_fundamental_risk,'live_execution':False,
            'policy':'Business quality and entry timing remain separate. Technical strength cannot override distress/accounting-risk flags, and fundamental quality does not imply immediate entry timing.'}
