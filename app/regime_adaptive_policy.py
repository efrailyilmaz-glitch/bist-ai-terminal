"""V97 regime-adaptive decision policy research layer.
Finds regime-specific shadow leaders from prospective policy decisions.
Recommendations are research-only and never switch the incumbent automatically.
"""
from __future__ import annotations
import sqlite3
from . import experience_engine as ex
from .decision_policy_challenger import POLICIES,_decision_utility

def analyze(horizon=20,min_regime_samples=10,min_selected=4):
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    with ex._LOCK:
        c=ex._conn();c.row_factory=sqlite3.Row
        rows=[dict(x) for x in c.execute(f'''SELECT p.signal_id,p.policy_id,p.policy_name,p.decision,
          s.regime,s.excess_{horizon} AS excess
          FROM policy_shadow p JOIN signals s ON s.id=p.signal_id
          WHERE s.settled_{horizon}=1 AND s.excess_{horizon} IS NOT NULL
          ORDER BY p.signal_id''').fetchall()];c.close()
    regimes=sorted({str(r.get('regime') or 'UNKNOWN').upper() for r in rows})
    out=[]
    for reg in regimes:
        rr=[r for r in rows if str(r.get('regime') or 'UNKNOWN').upper()==reg]
        policies=[]
        for p in POLICIES:
            pr=[r for r in rr if r['policy_id']==p['id']]
            selected=[float(r['excess']) for r in pr if r['decision'] in {'PASS','WATCH'}]
            no_trade=[float(r['excess']) for r in pr if r['decision']=='NO_TRADE']
            utility=[_decision_utility(r['decision'],r['excess']) for r in pr]
            mean_u=sum(utility)/len(utility) if utility else None
            mean_sel=sum(selected)/len(selected) if selected else None
            hit=sum(1 for x in selected if x>0)/len(selected)*100 if selected else None
            policies.append({'id':p['id'],'name':p['name'],'n':len(pr),'selected_n':len(selected),'no_trade_n':len(no_trade),
                             'mean_utility':None if mean_u is None else round(mean_u,3),
                             'selected_mean_excess_pct':None if mean_sel is None else round(mean_sel,3),
                             'selected_hit_rate_pct':None if hit is None else round(hit,2)})
        eligible=[x for x in policies if x['n']>=int(min_regime_samples) and x['selected_n']>=int(min_selected)]
        eligible.sort(key=lambda x:-(x['mean_utility'] if x['mean_utility'] is not None else -1e18))
        leader=eligible[0] if eligible else None
        incumbent=next((x for x in policies if x['id']=='incumbent'),None)
        margin=None if not leader or not incumbent or leader['mean_utility'] is None or incumbent['mean_utility'] is None else leader['mean_utility']-incumbent['mean_utility']
        recommendation='HOLD_INCUMBENT'
        if leader and leader['id']!='incumbent' and margin is not None and margin>=1.0:recommendation='SHADOW_REGIME_CHALLENGER'
        elif not leader:recommendation='INSUFFICIENT'
        out.append({'regime':reg,'leader':None if not leader else leader['id'],'leader_name':None if not leader else leader['name'],
                    'margin_vs_incumbent':None if margin is None else round(margin,3),'recommendation':recommendation,'policies':policies})
    return {'status':'OK','version':'97.0','horizon':horizon,'rows':out,
            'shadow_recommendations':[x for x in out if x['recommendation']=='SHADOW_REGIME_CHALLENGER'],
            'live_execution':False,
            'policy':'Regime-specific leaders are forward shadow observations only. No automatic regime-based policy switching or threshold mutation is permitted.'}
