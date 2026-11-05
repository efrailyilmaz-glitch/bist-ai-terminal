"""V100 unified research decision engine.
Consolidates committee, signal/trap guards, PIT/KAP integrity, alpha, fundamentals,
ensemble and smart-money/trap fusion into one explainable research decision.
Never authorizes execution.
"""
from __future__ import annotations
from .investment_committee import investment_committee
from .smart_money_trap_fusion import snapshot as fusion_snapshot

def decide(ticker,portfolio_value=1_000_000):
    code=ticker.upper().replace('.IS','')
    c=investment_committee(code,portfolio_value=portfolio_value)
    if c.get('status')!='OK':return {'ticker':code,'status':c.get('status','NO_DATA'),'final_decision':'NO_DATA'}
    fusion=fusion_snapshot(code)
    guard=c.get('signal_guard') or {};trap=c.get('trap_defense') or {}
    pit=c.get('point_in_time') or {};kap_pit=c.get('kap_point_in_time') or {}
    alpha=c.get('empirical') or {};premium=c.get('premium') or {};ensemble=c.get('ensemble') or {}
    opportunity=c.get('opportunity') or {}
    hard_vetoes=list(c.get('vetoes') or [])
    downgrades=[];supports=[]
    if fusion.get('state')=='BULLISH_CONFLICT_TRAP_RISK':downgrades.append('SMART_MONEY_TRAP_CONFLICT')
    if fusion.get('state')=='DISTRIBUTION_AND_TRAP_RISK':hard_vetoes.append('SMART_MONEY_DISTRIBUTION_TRAP')
    if fusion.get('state')=='CLEAN_ACCUMULATION_WATCH':supports.append('CLEAN_ACCUMULATION')
    if guard.get('status')=='CLEAR':supports.append('SIGNAL_GUARD_CLEAR')
    if trap.get('status')=='CLEAR':supports.append('TRAP_DEFENSE_CLEAR')
    if alpha.get('sample',0)>=15 and alpha.get('hit_probability',0)>=.55:supports.append('FORWARD_ALPHA_SUPPORT')
    if ensemble.get('agreement') not in {None,'LOW'}:supports.append('ENSEMBLE_AGREEMENT')
    if pit.get('status')=='BLOCK' or kap_pit.get('status')=='BLOCK':hard_vetoes.append('POINT_IN_TIME_INTEGRITY')
    hard_vetoes=list(dict.fromkeys(hard_vetoes))
    if hard_vetoes:
        final='NO_TRADE';final_tr='PAS GEÇ'
    elif c.get('decision')=='PASS' and not downgrades:
        final='RESEARCH_PASS';final_tr='ARAŞTIRMA ONAYI'
    elif c.get('decision')=='PASS' and downgrades:
        final='WATCH';final_tr='İZLE / TEYİT BEKLE'
    elif c.get('decision')=='WATCH':
        final='WATCH';final_tr='İZLE / TEYİT BEKLE'
    else:
        final='NO_TRADE';final_tr='PAS GEÇ'
    confidence=max(0,min(100,float(c.get('committee_score') or 0)))
    if fusion.get('state')=='CLEAN_ACCUMULATION_WATCH':confidence=min(100,confidence+3)
    if downgrades:confidence=max(0,confidence-8)
    if hard_vetoes:confidence=min(confidence,45)
    why=[
      {'module':'Investment Committee','status':c.get('decision'),'detail':c.get('decision_tr')},
      {'module':'Signal Guard','status':guard.get('status'),'detail':f"{guard.get('score','—')}/100"},
      {'module':'Trap Defense','status':trap.get('status'),'detail':f"{trap.get('score','—')}/100"},
      {'module':'Smart Money + Trap','status':fusion.get('state'),'detail':f"fusion {fusion.get('fusion_score','—')} · risk {fusion.get('risk_score','—')}"},
      {'module':'Point-in-Time','status':pit.get('status'),'detail':', '.join(pit.get('flags') or []) or 'OK'},
      {'module':'KAP PIT','status':kap_pit.get('status'),'detail':', '.join(kap_pit.get('flags') or []) or 'OK'},
      {'module':'Alpha','status':'SUPPORT' if 'FORWARD_ALPHA_SUPPORT' in supports else 'WEAK/UNKNOWN','detail':f"N={alpha.get('sample',0)} · hit {round(float(alpha.get('hit_probability',0))*100,1)}%"},
      {'module':'Ensemble','status':ensemble.get('agreement'),'detail':f"score {ensemble.get('ensemble_score','—')}"},
      {'module':'Fundamental/Valuation','status':'INFO','detail':f"health {premium.get('health_score','—')} · opportunity {opportunity.get('opportunity_score','—')}"},
    ]
    return {'ticker':code,'status':'OK','version':'100.0','final_decision':final,'final_decision_tr':final_tr,
            'confidence_score':round(confidence,1),'supports':supports,'downgrades':downgrades,'hard_vetoes':hard_vetoes,
            'why':why,'committee':c,'smart_money_trap':fusion,'live_execution':False,
            'note':'Unified research decision only. Hard integrity/risk gates can veto; supportive modules can never override a hard veto or authorize an order.'}
