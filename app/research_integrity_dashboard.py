"""V78 consolidated Research Integrity Dashboard.
Aggregates existing evidence/integrity controls without creating new alpha or live authority.
"""
from __future__ import annotations
from .experience_engine import verify_ledger
from .xs_paper import verify_lineage_ledger, history as xs_history
from .model_registry import history as model_history
from .pit_universe import dataset_status
from .protected_feature_governance import status as protected_status
from .forward_scorecard import build as scorecard_build
from .data_quality_guard import evaluate_history as data_quality_history
from .portfolio_stress_lab import evaluate as stress_history
from .decay_v2 import detect_xs_decay

def _panel(name,data,ok_values=('PASS','OK','PIT_VERIFIED')):
    st=(data or {}).get('status')
    return {'name':name,'status':st,'healthy':st in ok_values,'data':data}

def dashboard(portfolio_id=None,days=0,test_count=3):
    panels=[]
    evidence=verify_ledger();panels.append(_panel('FORWARD_EVIDENCE_LEDGER',evidence))
    lineage=verify_lineage_ledger();panels.append(_panel('XS_LINEAGE_HASH_CHAIN',lineage))
    pit=dataset_status();panels.append(_panel('POINT_IN_TIME_UNIVERSE',pit))
    protected=protected_status(100);panels.append(_panel('PROTECTED_FEATURE_GOVERNANCE',protected,('OK',)))
    models=model_history(20);panels.append(_panel('MODEL_REPRODUCIBILITY_REGISTRY',models,('OK',)))
    portfolio=None
    if portfolio_id is not None:
        h=xs_history(int(portfolio_id),1000)
        if h.get('status')!='OK':
            portfolio={'status':'NOT_FOUND','portfolio_id':int(portfolio_id)}
        else:
            score=scorecard_build(h,max(0,int(days)),max(1,int(test_count)))
            dataq=data_quality_history(h)
            stress=stress_history(h)
            decay=detect_xs_decay(h)
            portfolio={'status':'OK','portfolio_id':int(portfolio_id),'forward_scorecard':score,
                       'data_quality':dataq,'portfolio_stress':stress,'decay':decay}
            panels.extend([
                _panel('FORWARD_EVIDENCE_SCORECARD',score,('ELIGIBLE_FOR_REVIEW',)),
                _panel('PORTFOLIO_DATA_QUALITY',dataq),
                _panel('PORTFOLIO_STRESS',stress),
                _panel('PORTFOLIO_DECAY',decay,('HEALTHY','WATCH','OK')),
            ])
    blockers=[]
    warnings=[]
    for p in panels:
        st=p.get('status')
        if st in {'FAIL','BLOCK','ERROR','NOT_FOUND'}:blockers.append(p['name'])
        elif not p.get('healthy'):warnings.append(p['name'])
    overall='BLOCK' if blockers else ('WARN' if warnings else 'PASS')
    return {'status':overall,'portfolio':portfolio,'panels':panels,'blockers':blockers,'warnings':warnings,
            'counts':{'panels':len(panels),'blockers':len(blockers),'warnings':len(warnings)},
            'policy':'Integrity dashboard is explanatory and veto-oriented. It never creates alpha, increases risk, or authorizes live execution.'}
