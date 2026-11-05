"""V117 Research Integrity Master Dashboard.
Aggregates the current research safety/governance layers into one veto-oriented system view.
It creates no alpha and has no live execution authority.
"""
from __future__ import annotations
from .research_integrity_dashboard import dashboard as integrity_dashboard
from .data_provider_trust_v2 import snapshot as data_trust
from .feature_governance_v3 import report as feature_governance
from .confidence_calibration import analyze as confidence_calibration
from .policy_promotion_governance import report as policy_promotion
from .research_factory_v2 import status as factory_status
from .experience_engine import verify_ledger, calibration as experience_calibration

def dashboard():
    integrity=integrity_dashboard()
    trust=data_trust([])
    feat=feature_governance(20,30)
    conf=confidence_calibration(20,0.0,5)
    promo=policy_promotion()
    factory=factory_status(20)
    ledger=verify_ledger()
    exp=experience_calibration()
    panels=[
      {'id':'data_trust','name':'Data Trust 2.0','status':trust.get('status'),'critical':True,
       'detail':{'trust_score':trust.get('trust_score'),'blocks':trust.get('critical_blocks') or []}},
      {'id':'research_integrity','name':'Research Integrity','status':integrity.get('status'),'critical':True,
       'detail':{'blockers':integrity.get('blockers') or [],'warnings':integrity.get('warnings') or []}},
      {'id':'evidence_ledger','name':'Forward Evidence Ledger','status':ledger.get('status'),'critical':True,
       'detail':{'rows':ledger.get('rows'),'bad_ids':ledger.get('bad_ids') or []}},
      {'id':'feature_governance','name':'Feature Governance 3.0','status':'BLOCK' if any(x.get('state')=='LEAKAGE_RISK_BLOCK' for x in feat.get('rows',[])) else 'WARN' if any(x.get('state') in {'DECAY_REVIEW','UNREGISTERED_RESEARCH_ONLY'} for x in feat.get('rows',[])) else 'PASS',
       'critical':True,'detail':{'summary':feat.get('summary') or {},'redundancy_pairs':len(feat.get('redundancy_pairs') or [])}},
      {'id':'confidence','name':'Confidence Calibration','status':conf.get('status'),'critical':False,
       'detail':{'ece':conf.get('expected_calibration_error'),'brier':conf.get('brier_score'),'n':conf.get('settled_selected')}},
      {'id':'policy_promotion','name':'Policy Promotion Governance','status':'REVIEW' if promo.get('review_candidates') else 'PASS','critical':False,
       'detail':{'review_candidates':[x.get('policy_id') for x in promo.get('review_candidates') or []]}},
      {'id':'research_factory','name':'Research Factory','status':'PASS','critical':False,
       'detail':{'runs':len(factory.get('runs') or []),'last':(factory.get('runs') or [{}])[0].get('status') if factory.get('runs') else None}},
      {'id':'decision_experience','name':'Decision Experience','status':'PASS' if (exp.get('total_signals') or 0)>0 else 'WARN','critical':False,
       'detail':{'total_signals':exp.get('total_signals'),'overall':exp.get('overall')}},
    ]
    blockers=[p['id'] for p in panels if p['critical'] and p['status'] in {'BLOCK','FAIL','DATA_BLOCK','ERROR'}]
    warnings=[p['id'] for p in panels if p['status'] in {'WARN','CAUTION','OVERCONFIDENT','UNDERCONFIDENT','INSUFFICIENT','REVIEW'}]
    score=100
    score-=25*len(blockers);score-=5*len(warnings)
    score=max(0,min(100,score))
    overall='BLOCK' if blockers else 'WARN' if warnings else 'PASS'
    return {'status':overall,'version':'117.0','system_trust_score':score,'panels':panels,
            'blockers':blockers,'warnings':warnings,
            'research_decision_allowed':not bool(blockers),'live_execution':False,
            'policy':'Master dashboard is veto-oriented. Critical integrity failures block new research decisions; no panel can create alpha, increase exposure, promote production or authorize live execution.'}
