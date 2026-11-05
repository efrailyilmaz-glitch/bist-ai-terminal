"""V101 portfolio-level decision intelligence.
Combines portfolio risk/correlation, sector concentration and single-name unified decisions.
A good stock can still be deferred or blocked for portfolio-level reasons.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from .portfolio_analytics import analyze_portfolio
from .portfolio_guard import portfolio_entry_guard
from .fundamentals import get_fundamentals
from .unified_decision_engine import decide as unified_decide

def _sectors(codes,weights):
    out={}
    with ThreadPoolExecutor(max_workers=6) as pool:
        fut={pool.submit(get_fundamentals,c):c for c in codes}
        for q in as_completed(fut):
            code=fut[q]
            try:r=q.result();sec=r.get('sector') or 'Unknown'
            except Exception:sec='Unknown'
            w=float(weights.get(code,0));z=out.setdefault(sec,{'sector':sec,'weight_pct':0.0,'tickers':[]})
            z['weight_pct']+=w;z['tickers'].append(code)
    rows=list(out.values())
    for x in rows:x['weight_pct']=round(x['weight_pct'],2)
    rows.sort(key=lambda x:-x['weight_pct'])
    return rows

def analyze(codes,candidate=None,method='equal',portfolio_value=1_000_000):
    codes=list(dict.fromkeys([str(x).upper().replace('.IS','') for x in (codes or []) if x]))[:12]
    if not codes:return {'status':'NO_CODES'}
    base=analyze_portfolio(codes,method)
    if base.get('status')!='OK':return {'status':base.get('status'),'portfolio':base}
    weights={x['ticker']:float(x.get('weight_pct') or 0) for x in (base.get('risk_rows') or [])}
    sectors=_sectors(base.get('tickers') or codes,weights)
    flags=[]
    if float(base.get('avg_correlation') or 0)>=.65:flags.append('HIGH_AVERAGE_CORRELATION')
    if float(base.get('diversification_score') or 100)<35:flags.append('LOW_DIVERSIFICATION')
    if any(float(x.get('risk_contribution_pct') or 0)>=35 for x in (base.get('risk_rows') or [])):flags.append('SINGLE_NAME_RISK_CONTRIBUTION')
    if sectors and float(sectors[0].get('weight_pct') or 0)>=40:flags.append('SECTOR_CONCENTRATION')
    candidate_result=None
    if candidate:
        cand=str(candidate).upper().replace('.IS','')
        unified=unified_decide(cand,portfolio_value=portfolio_value)
        positions={c:{'quantity':1} for c in codes}
        guard=portfolio_entry_guard(cand,positions,'BUY')
        expanded=analyze_portfolio(list(dict.fromkeys(codes+[cand])),method)
        candidate_flags=[]
        if unified.get('final_decision')=='NO_TRADE':candidate_flags.append('SINGLE_NAME_NO_TRADE')
        if guard.get('status')=='BLOCK':candidate_flags+=list(guard.get('flags') or ['PORTFOLIO_GUARD_BLOCK'])
        elif guard.get('status')=='CAUTION':candidate_flags+=list(guard.get('flags') or ['PORTFOLIO_GUARD_CAUTION'])
        if expanded.get('status')=='OK' and float(expanded.get('avg_correlation') or 0)>=.70:candidate_flags.append('POST_ADD_CORRELATION_HIGH')
        if 'SINGLE_NAME_NO_TRADE' in candidate_flags or guard.get('status')=='BLOCK':
            decision='PORTFOLIO_BLOCK'
        elif candidate_flags or flags:
            decision='DEFER_OR_DERISK'
        elif unified.get('final_decision')=='RESEARCH_PASS':
            decision='PORTFOLIO_ACCEPTABLE_RESEARCH'
        else:
            decision='WATCH'
        candidate_result={'ticker':cand,'decision':decision,'flags':list(dict.fromkeys(candidate_flags)),
                          'unified_decision':unified.get('final_decision'),'unified_confidence':unified.get('confidence_score'),
                          'entry_guard':guard,'expanded_portfolio':expanded}
    overall='BLOCK' if any(x in flags for x in ['HIGH_AVERAGE_CORRELATION','SINGLE_NAME_RISK_CONTRIBUTION']) else 'CAUTION' if flags else 'CLEAR'
    return {'status':'OK','version':'101.0','portfolio_status':overall,'flags':flags,'portfolio':base,'sectors':sectors,
            'candidate':candidate_result,'live_execution':False,
            'note':'Portfolio-level research intelligence. Correlation, sector concentration and tail-risk guards can defer a good single-name setup; no order is authorized.'}
