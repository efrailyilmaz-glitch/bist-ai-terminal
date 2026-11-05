"""V120 full repository/runtime integrity audit.
Checks source syntax, static wiring, duplicate routes/views and critical module presence.
It is diagnostic only and never changes trading/research state.
"""
from __future__ import annotations
import re
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parent

CRITICAL_MODULES=[
 'decision_policy_challenger.py','decision_policy_tournament.py','policy_promotion_governance.py',
 'gate_threshold_challenger.py','gate_interaction_analysis.py','decision_error_cost.py',
 'confidence_calibration.py','regime_adaptive_policy.py','adversarial_v3.py',
 'smart_money_trap_fusion.py','unified_decision_engine.py','portfolio_decision_intelligence.py',
 'dynamic_position_sizing.py','portfolio_crash_scenarios.py','execution_reality_v2.py',
 'capacity_scale_analysis.py','data_provider_trust_v2.py','kap_intelligence_v2.py',
 'fundamental_price_fusion.py','cross_sectional_ranking_v2.py','sector_factor_neutral_v2.py',
 'model_zoo_v2.py','feature_governance_v3.py','research_factory_v2.py','research_integrity_master.py','live_data_adapters.py','broker_sandbox.py','controlled_live_readiness.py'
]

def _python_syntax():
    bad=[];checked=0
    for p in BASE.glob('*.py'):
        checked+=1
        try:compile(p.read_text(encoding='utf-8'),str(p),'exec')
        except Exception as e:bad.append({'file':p.name,'error':str(e)[:180]})
    return {'status':'PASS' if not bad else 'FAIL','checked':checked,'bad':bad}

def _static_wiring():
    idx=(BASE/'templates'/'index.html').read_text(encoding='utf-8')
    refs=re.findall(r'(?:src|href)="(/static/[^"?]+)',idx)
    names=[x.split('/static/',1)[1] for x in refs]
    missing=[x for x in names if not (BASE/'static'/x).exists()]
    dup=sorted({x for x in names if names.count(x)>1})
    return {'status':'PASS' if not missing and not dup else 'FAIL','refs':len(names),'missing':missing,'duplicates':dup}

def _navigation():
    idx=(BASE/'templates'/'index.html').read_text(encoding='utf-8')
    views=re.findall(r'data-view="([^"]+)"',idx)
    dup=sorted({x for x in views if views.count(x)>1})
    groups=idx.count('<details class="navGroup"')
    return {'status':'PASS' if not dup and groups==5 else 'WARN','views':len(views),'groups':groups,'duplicate_views':dup}

def _routes():
    src=(BASE/'main.py').read_text(encoding='utf-8')
    routes=re.findall(r"@app\.(?:get|post|delete|put)\('([^']+)'",src)
    dup=sorted({x for x in routes if routes.count(x)>1})
    return {'status':'PASS' if not dup else 'FAIL','routes':len(routes),'duplicates':dup}

def _modules():
    missing=[x for x in CRITICAL_MODULES if not (BASE/x).exists()]
    return {'status':'PASS' if not missing else 'FAIL','required':len(CRITICAL_MODULES),'missing':missing}

def _version(expected):
    idx=(BASE/'templates'/'index.html').read_text(encoding='utf-8')
    main=(BASE/'main.py').read_text(encoding='utf-8')
    ok=(f'V{expected}' in idx and f"version='{expected}'" in main and f"'version':'{expected}'" in main)
    return {'status':'PASS' if ok else 'FAIL','expected':expected}

def audit(expected_version='120.0.0'):
    checks={
      'python_syntax':_python_syntax(),
      'static_wiring':_static_wiring(),
      'navigation':_navigation(),
      'routes':_routes(),
      'critical_modules':_modules(),
      'version_consistency':_version(expected_version),
    }
    blockers=[k for k,v in checks.items() if v.get('status')=='FAIL']
    warnings=[k for k,v in checks.items() if v.get('status')=='WARN']
    status='FAIL' if blockers else 'WARN' if warnings else 'PASS'
    return {'status':status,'version':'120.0','blockers':blockers,'warnings':warnings,'checks':checks,
            'policy':'Read-only integrity audit. It detects wiring/source inconsistencies and never enables execution or mutates research governance.'}
