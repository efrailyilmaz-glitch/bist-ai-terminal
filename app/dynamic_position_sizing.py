"""V102 dynamic research position sizing.
Starts from the committee's already-capped research position and applies only non-increasing
confidence, regime, deception-risk and portfolio-risk multipliers. Never enlarges exposure.
"""
from __future__ import annotations
from .unified_decision_engine import decide as unified_decide
from .portfolio_decision_intelligence import analyze as portfolio_intelligence

REGIME_MULT={'BULL':1.0,'SIDEWAYS':.80,'HIGH_VOL_SIDEWAYS':.60,'BEAR':.50,'UNKNOWN':.65}

def size(ticker,portfolio_value=1_000_000,portfolio_codes=None):
    code=ticker.upper().replace('.IS','')
    u=unified_decide(code,portfolio_value=portfolio_value)
    if u.get('status')!='OK':return {'ticker':code,'status':u.get('status','NO_DATA')}
    c=u.get('committee') or {};ps=c.get('position_sizing') or {}
    base=max(0.0,float(ps.get('research_position_value') or 0))
    base_pct=max(0.0,float(ps.get('research_position_pct') or 0))
    conf=max(0.0,min(100.0,float(u.get('confidence_score') or 0)))
    confidence_mult=max(.35,min(1.0,(conf-35)/65)) if conf>35 else 0.0
    regime=str(c.get('regime') or 'UNKNOWN').upper();regime_mult=REGIME_MULT.get(regime,.65)
    fusion=u.get('smart_money_trap') or {};risk=float(fusion.get('risk_score') or 50)
    trap_mult=max(.25,min(1.0,1-risk/125.0))
    if u.get('final_decision')=='WATCH':decision_mult=.55
    elif u.get('final_decision')=='RESEARCH_PASS':decision_mult=1.0
    else:decision_mult=0.0
    portfolio_mult=1.0;portfolio_detail=None
    codes=list(portfolio_codes or [])
    if codes:
        p=portfolio_intelligence(codes,candidate=code,method='equal',portfolio_value=portfolio_value)
        portfolio_detail=p.get('candidate') or {}
        d=portfolio_detail.get('decision')
        guard=portfolio_detail.get('entry_guard') or {}
        portfolio_mult=max(0.0,min(1.0,float(guard.get('risk_multiplier') if guard.get('risk_multiplier') is not None else 1.0)))
        if d=='PORTFOLIO_BLOCK':portfolio_mult=0.0
        elif d=='DEFER_OR_DERISK':portfolio_mult=min(portfolio_mult,.50)
    multipliers={'confidence':round(confidence_mult,3),'regime':round(regime_mult,3),'trap_distribution':round(trap_mult,3),
                 'decision':round(decision_mult,3),'portfolio':round(portfolio_mult,3)}
    final_mult=min(multipliers.values()) if multipliers else 0.0
    # Conservative composition: multiply but never exceed the weakest guard or the committee base.
    combined=confidence_mult*regime_mult*trap_mult*decision_mult*portfolio_mult
    combined=max(0.0,min(final_mult,combined,1.0))
    amount=min(base,base*combined);pct=min(base_pct,base_pct*combined)
    return {'ticker':code,'status':'OK','version':'102.0','base_committee_amount':round(base,2),'base_committee_pct':round(base_pct,3),
            'multipliers':multipliers,'combined_multiplier':round(combined,4),
            'dynamic_research_amount':round(amount,2),'dynamic_research_pct':round(pct,3),
            'regime':regime,'unified_decision':u.get('final_decision'),'confidence_score':conf,
            'portfolio_context':portfolio_detail,'live_execution':False,
            'policy':'Dynamic sizing can only reduce the committee-capped research position. It cannot enlarge exposure, bypass a veto or place an order.'}
