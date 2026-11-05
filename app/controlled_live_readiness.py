"""V126 controlled live-readiness gate.
This module never enables execution. It only states whether the system is ready for a manual,
separately authorized integration review.
"""
from __future__ import annotations
from .broker_bridge import broker_status
from .broker_sandbox import status as sandbox_status
from .live_data_adapters import registry as live_data_registry
from .desktop_readiness import status as desktop_status
from .research_integrity_master import dashboard as integrity_master
from .experience_engine import calibration as experience_calibration
from .policy_promotion_governance import report as policy_promotion_report

def report(min_settled_20d=30,min_total_signals=50):
    broker=broker_status()
    sandbox=sandbox_status()
    live_data=live_data_registry()
    desktop=desktop_status()
    integrity=integrity_master()
    exp=experience_calibration()
    promo=policy_promotion_report()

    settled20=int((((exp.get('overall') or {}).get('20d') or {}).get('n') or 0))
    total=int(exp.get('total_signals') or 0)
    promotion_candidates=promo.get('review_candidates') or []
    realtime_connected=int(live_data.get('connected_realtime') or 0)

    gates=[]
    def gate(name,passed,detail,category):
        gates.append({'name':name,'pass':bool(passed),'detail':detail,'category':category,'hard':True})

    gate('Research integrity',integrity.get('status')!='BLOCK' and bool(integrity.get('research_decision_allowed')),
         {'status':integrity.get('status'),'score':integrity.get('system_trust_score'),'blockers':integrity.get('blockers') or []},'INTERNAL')
    gate('Desktop/runtime readiness',desktop.get('status')=='PASS',
         {'status':desktop.get('status'),'blockers':desktop.get('blockers') or []},'INTERNAL')
    gate('Broker sandbox safeguards',sandbox.get('status')=='OK' and not sandbox.get('direct_live_execution_enabled'),
         {'status':sandbox.get('status'),'kill_switch':sandbox.get('kill_switch'),'controls':sandbox.get('controls') or []},'INTERNAL')
    gate('Direct-live lock remains closed',not bool(broker.get('direct_live_execution_enabled')),
         {'direct_live_execution_enabled':broker.get('direct_live_execution_enabled')},'SAFETY_LOCK')
    gate('Minimum prospective evidence',total>=int(min_total_signals) and settled20>=int(min_settled_20d),
         {'total_signals':total,'settled_20d':settled20,'required_total':int(min_total_signals),'required_20d':int(min_settled_20d)},'FORWARD_EVIDENCE')
    gate('Policy promotion evidence',len(promotion_candidates)>0,
         {'review_candidates':[x.get('policy_id') for x in promotion_candidates]},'FORWARD_EVIDENCE')
    gate('Licensed realtime market feed',realtime_connected>=1,
         {'connected_realtime':realtime_connected,'providers':live_data.get('rows') or []},'EXTERNAL_DEPENDENCY')
    gate('Verified official broker contract',False,
         {'configured':bool(broker.get('direct_official_api_configured')),
          'reason':'No verified official live-order adapter/contract is implemented in BIST AI Terminal.'},'EXTERNAL_DEPENDENCY')

    blockers=[g['name'] for g in gates if g['hard'] and not g['pass']]
    internal=[g['name'] for g in gates if not g['pass'] and g['category'] in {'INTERNAL','FORWARD_EVIDENCE'}]
    external=[g['name'] for g in gates if not g['pass'] and g['category']=='EXTERNAL_DEPENDENCY']
    safety=[g['name'] for g in gates if not g['pass'] and g['category']=='SAFETY_LOCK']

    ready=not blockers
    status='READY_FOR_MANUAL_INTEGRATION_REVIEW' if ready else 'NOT_READY_FOR_LIVE'
    return {
      'status':status,'version':'126.0','gates':gates,'blockers':blockers,
      'internal_blockers':internal,'external_blockers':external,'safety_blockers':safety,
      'direct_live_execution_enabled':False,
      'automatic_live_enable_supported':False,
      'next_step':'Manual provider/broker integration review only' if ready else 'Resolve blockers while keeping direct live execution locked',
      'policy':'This is a readiness report, not execution authority. Passing all gates still requires a separate human-controlled broker integration and security review; this module contains no live-order method.'
    }
