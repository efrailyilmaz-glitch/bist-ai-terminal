"""V77 forward evidence scorecard for XS paper challengers.
Consolidates existing governance evidence; it does not create alpha or authorize live execution.
"""
from __future__ import annotations
from .promotion_governance import evaluate as hard_gate
from .statistical_promotion import evaluate as statistical_gate
from .regime_robustness import evaluate as regime_gate
from .data_quality_guard import evaluate_history as data_quality_gate
from .factor_neutralization import evaluate_history as factor_gate
from .portfolio_stress_lab import evaluate as stress_gate
from .decay_v2 import detect_xs_decay

def build(history,days,test_count=3):
    hard=hard_gate(history,days)
    stats=statistical_gate(history,test_count=max(1,int(test_count))) if hard.get('status')=='PROMOTION_REVIEW' else {'status':'NOT_RUN','reasons':['HARD_GATE_NOT_PASSED']}
    regime=regime_gate(history) if stats.get('status')=='PASS' else {'status':'NOT_RUN','reasons':['STATISTICAL_GATE_NOT_PASSED']}
    dataq=data_quality_gate(history) if regime.get('status')=='PASS' else {'status':'NOT_RUN','reasons':['REGIME_GATE_NOT_PASSED']}
    factor=factor_gate(history) if dataq.get('status')=='PASS' else {'status':'NOT_RUN','reasons':['DATA_QUALITY_GATE_NOT_PASSED']}
    stress=stress_gate(history) if factor.get('status')=='PASS' else {'status':'NOT_RUN','reasons':['FACTOR_GATE_NOT_PASSED']}
    decay=detect_xs_decay(history)
    components=[
      ('HARD_FORWARD_GOVERNANCE',hard,'PROMOTION_REVIEW'),
      ('STATISTICAL_CONFIDENCE',stats,'PASS'),
      ('REGIME_ROBUSTNESS',regime,'PASS'),
      ('DATA_QUALITY',dataq,'PASS'),
      ('FACTOR_NEUTRALITY',factor,'PASS'),
      ('PORTFOLIO_STRESS',stress,'PASS'),
    ]
    rows=[];passed=0;reasons=[]
    for name,obj,ok in components:
        status=obj.get('status')
        good=status==ok
        if good:passed+=1
        rows.append({'component':name,'status':status,'passed':good,'reasons':obj.get('reasons') or []})
        reasons.extend(obj.get('reasons') or [])
    if decay.get('status')=='DECAY':
        reasons.append('MODEL_DECAY')
        rows.append({'component':'DECAY_MONITOR','status':'DECAY','passed':False,'reasons':['MODEL_DECAY']})
    else:
        passed+=1
        rows.append({'component':'DECAY_MONITOR','status':decay.get('status'),'passed':True,'reasons':[]})
    total=len(rows)
    eligible=(passed==total and hard.get('status')=='PROMOTION_REVIEW')
    overall='ELIGIBLE_FOR_REVIEW' if eligible else ('BLOCK' if any(r['status']=='BLOCK' for r in rows) else 'OBSERVE')
    return {'status':overall,'evidence_score_pct':round(passed/max(1,total)*100,1),
            'passed_components':passed,'total_components':total,'reasons':list(dict.fromkeys(reasons)),
            'components':rows,
            'summary':{'forward_days':int(days),'hard_metrics':hard.get('metrics') or {},
                       'decay_status':decay.get('status')},
            'policy':'This scorecard explains forward evidence only. It cannot promote to live execution and cannot override a failed gate.'}
