"""V63 data-quality and survivorship guard for XS research/promotion.
Conservative by design: bad or uncertain data can only veto/downgrade.
"""
from __future__ import annotations
import math
from collections import Counter

def _f(x,default=None):
    try:
        z=float(x)
        return z if math.isfinite(z) else default
    except Exception:return default

def audit_current_snapshot(rows,requested=None,min_coverage_pct=80.0,max_stale_share_pct=10.0,max_jump_share_pct=5.0):
    rows=list(rows or [])
    requested=max(len(rows),int(requested or len(rows) or 0))
    flags=[];details={}
    if requested<=0:
        return {'status':'BLOCK','flags':['NO_REQUESTED_UNIVERSE'],'details':{}}
    coverage=len(rows)/requested*100
    details['coverage_pct']=round(coverage,2)
    if coverage<min_coverage_pct:flags.append('LOW_CURRENT_COVERAGE')
    dates=[str(x.get('as_of') or x.get('date') or '')[:10] for x in rows if x.get('as_of') or x.get('date')]
    mode=None
    if dates:
        mode=Counter(dates).most_common(1)[0][0]
        stale=sum(1 for d in dates if d!=mode)/max(1,len(dates))*100
    else:
        stale=100.0
    details['dominant_as_of']=mode;details['stale_share_pct']=round(stale,2)
    if stale>max_stale_share_pct:flags.append('STALE_OR_MIXED_AS_OF')
    bad_price=sum(1 for x in rows if (_f(x.get('price'),0) or 0)<=0)
    details['bad_price_count']=bad_price
    if bad_price:flags.append('INVALID_PRICE')
    jumps=0
    for x in rows:
        r1=_f(x.get('ret_1'))
        if r1 is not None and abs(r1)>.35:jumps+=1
    jump_share=jumps/max(1,len(rows))*100
    details['extreme_jump_share_pct']=round(jump_share,2)
    if jump_share>max_jump_share_pct:flags.append('EXTREME_RETURN_CLUSTER')
    status='PASS'
    hard={'LOW_CURRENT_COVERAGE','STALE_OR_MIXED_AS_OF','INVALID_PRICE'}
    if any(f in hard for f in flags):status='BLOCK'
    elif flags:status='CAUTION'
    return {'status':status,'flags':flags,'details':details,
            'policy':'Bad/uncertain data can only reduce confidence or block a new ranking.'}

def audit_training_panel(panel_meta):
    requested=int((panel_meta or {}).get('requested') or 0)
    symbols=int((panel_meta or {}).get('symbols') or 0)
    failed=(panel_meta or {}).get('failed') or []
    coverage=(symbols/requested*100) if requested else 0.0
    flags=[]
    if requested and coverage<80:flags.append('LOW_TRAINING_SYMBOL_COVERAGE')
    if len(failed)>max(5,int(requested*.15)):flags.append('HIGH_FAILED_SYMBOL_COUNT')
    return {'status':'BLOCK' if flags else 'PASS','flags':flags,
            'details':{'coverage_pct':round(coverage,2),'failed_symbols':len(failed),'requested':requested,'symbols':symbols}}

def survivorship_guard(historical_universe_point_in_time=False,current_universe_proxy=True):
    flags=[]
    if not historical_universe_point_in_time:flags.append('HISTORICAL_UNIVERSE_NOT_POINT_IN_TIME')
    if current_universe_proxy:flags.append('CURRENT_UNIVERSE_PROXY')
    return {'status':'CAUTION' if flags else 'PASS','flags':flags,
            'survivorship_bias_risk':bool(flags),
            'policy':'Historical research using today\'s surviving universe is never treated as fully point-in-time.'}

def promotion_gate(history,ranking_integrity=None,universe_integrity=None):
    ranking_integrity=ranking_integrity or {}
    universe_integrity=universe_integrity or {}
    reasons=[]
    if ranking_integrity.get('status')=='BLOCK':reasons.append('RANKING_DATA_INTEGRITY_BLOCK')
    if universe_integrity.get('status') not in {'PASS',None}:reasons.append('SURVIVORSHIP_RISK_UNRESOLVED')
    rebs=(history or {}).get('rebalances') or []
    malformed=sum(1 for r in rebs if not r.get('ranking_as_of') or not r.get('ranking_snapshot_json'))
    if rebs and malformed:reasons.append('REBAlANCE_DATA_LINEAGE_INCOMPLETE')
    return {'status':'PASS' if not reasons else 'OBSERVE','reasons':reasons,
            'ranking_integrity':ranking_integrity,'universe_integrity':universe_integrity,
            'policy':'Data-quality/survivorship findings can only veto promotion.'}
