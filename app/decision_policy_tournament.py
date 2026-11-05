"""V91 multi-horizon decision policy tournament.
Combines 5/20/60 day prospective shadow evidence without allowing a single horizon to dominate.
"""
from __future__ import annotations
import math,statistics
from .decision_policy_challenger import report,POLICIES

WEIGHTS={5:0.20,20:0.50,60:0.30}

def _num(x,d=None):
    try:
        z=float(x)
        return z if math.isfinite(z) else d
    except Exception:return d

def tournament(min_settled=12):
    reports={h:report(h,min_settled=min_settled) for h in (5,20,60)}
    rows=[]
    for p in POLICIES:
        pid=p['id'];hs=[];mature=0;supported=0
        for h,r in reports.items():
            row=next((x for x in (r.get('rows') or []) if x.get('id')==pid),None)
            pair=next((x for x in (r.get('paired_comparisons') or []) if x.get('challenger')==pid),None)
            if not row:continue
            score=_num(row.get('shadow_score'),0)
            status=row.get('status')
            if status=='MATURE':mature+=1
            if pair and pair.get('status')=='SUPPORTED':supported+=1
            hs.append({'horizon':h,'weight':WEIGHTS[h],'shadow_score':score,'status':status,
                       'selected_mean_excess_pct':row.get('selected_mean_excess_pct'),
                       'selected_hit_rate_pct':row.get('selected_hit_rate_pct'),
                       'paired_status':None if not pair else pair.get('status'),
                       'paired_delta':None if not pair else pair.get('mean_utility_delta')})
        vals=[x['shadow_score'] for x in hs]
        weighted=sum(x['shadow_score']*x['weight'] for x in hs)
        dispersion=statistics.pstdev(vals) if len(vals)>1 else 0.0
        penalty=min(5.0,dispersion*.35)
        composite=weighted-penalty
        cross_horizon_ok=mature>=2
        status='MATURE' if cross_horizon_ok else 'OBSERVE'
        rows.append({'id':pid,'name':p['name'],'status':status,'mature_horizons':mature,
                     'supported_horizons':supported,'composite_score':round(composite,3),
                     'horizon_dispersion':round(dispersion,3),'dispersion_penalty':round(penalty,3),
                     'horizons':hs})
    rows.sort(key=lambda x:(x['status']!='MATURE',-x['composite_score'],x['id']))
    incumbent=next((x for x in rows if x['id']=='incumbent'),None)
    best=rows[0] if rows else None
    decision={'action':'HOLD','reason':'NO_MATURE_MULTI_HORIZON_CHALLENGER'}
    if best and incumbent and best['id']!='incumbent' and best['status']=='MATURE' and incumbent['status']=='MATURE':
        margin=best['composite_score']-incumbent['composite_score']
        if best['supported_horizons']>=2 and margin>=1.0:
            decision={'action':'TOURNAMENT_REVIEW','challenger':best['id'],'margin':round(margin,3),
                      'reason':'MULTI_HORIZON_FORWARD_EDGE'}
        elif best['supported_horizons']<2:
            decision={'action':'HOLD','reason':'INSUFFICIENT_SUPPORTED_HORIZONS'}
        else:
            decision={'action':'HOLD','reason':'NO_MULTI_HORIZON_MARGIN'}
    return {'status':'OK','version':'91.0','weights':WEIGHTS,'rows':rows,'decision':decision,
            'live_execution':False,
            'policy':'Tournament is prospective and multi-horizon. A single 5d/20d/60d result cannot win alone; tournament review never changes production policy automatically.'}
