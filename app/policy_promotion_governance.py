"""V92 promotion governance for decision-policy shadow challengers.
Only settled prospective evidence is eligible. Passing this module means review eligibility,
never automatic incumbent replacement and never live execution authorization.
"""
from __future__ import annotations
from datetime import datetime
from . import experience_engine as ex
from .decision_policy_challenger import report as challenger_report
from .decision_policy_tournament import tournament

def _max_drawdown(points):
    peak=0.0;cum=0.0;maxdd=0.0
    for x in points:
        cum+=float(x);peak=max(peak,cum);maxdd=max(maxdd,peak-cum)
    return maxdd

def evaluate(policy_id,horizon=20,min_forward_days=90,min_signals=30,min_regimes=2,max_utility_drawdown=10.0,max_miss_rate_pct=25.0):
    if policy_id=='incumbent':return {'status':'NOT_APPLICABLE','policy_id':policy_id,'reasons':['INCUMBENT_IS_NOT_A_CHALLENGER']}
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    rep=challenger_report(horizon,min_settled=max(12,min_signals))
    tourn=tournament(min_settled=max(12,min_signals))
    row=next((x for x in (rep.get('rows') or []) if x.get('id')==policy_id),None)
    pair=next((x for x in (rep.get('paired_comparisons') or []) if x.get('challenger')==policy_id),None)
    tr=next((x for x in (tourn.get('rows') or []) if x.get('id')==policy_id),None)
    with ex._LOCK:
        c=ex._conn();c.row_factory=__import__('sqlite3').Row
        rows=[dict(x) for x in c.execute(f'''SELECT p.signal_id,p.decision,s.created_epoch,s.regime,s.excess_{horizon} AS excess
          FROM policy_shadow p JOIN signals s ON s.id=p.signal_id
          WHERE p.policy_id=? AND s.settled_{horizon}=1 AND s.excess_{horizon} IS NOT NULL
          ORDER BY s.created_epoch''',(str(policy_id),)).fetchall()]
        c.close()
    epochs=[float(x['created_epoch']) for x in rows]
    span_days=(max(epochs)-min(epochs))/86400 if len(epochs)>=2 else 0.0
    selected=[float(x['excess']) for x in rows if x['decision'] in {'PASS','WATCH'}]
    no_trade=[float(x['excess']) for x in rows if x['decision']=='NO_TRADE']
    maxdd=_max_drawdown(selected)
    missed=sum(1 for x in no_trade if x>=3)
    miss_rate=missed/max(1,len(no_trade))*100
    regime_counts={}
    for x in rows:
        reg=str(x.get('regime') or 'UNKNOWN').upper();regime_counts[reg]=regime_counts.get(reg,0)+1
    covered=sum(1 for n in regime_counts.values() if n>=5)
    persistence=((rep.get('persistence') or {}).get('states') or {}).get(policy_id) or {}
    gates=[]
    def gate(name,passed,detail,hard=True):
        gates.append({'name':name,'pass':bool(passed),'detail':detail,'hard':hard})
    gate('Minimum forward span',span_days>=float(min_forward_days),f'{span_days:.1f} / {min_forward_days} days')
    gate('Minimum settled signals',len(rows)>=int(min_signals),f'{len(rows)} / {min_signals}')
    gate('Paired CI support',bool(pair and pair.get('status')=='SUPPORTED' and (pair.get('ci_low') or 0)>0),f"{None if not pair else pair.get('status')} · CI {None if not pair else pair.get('ci_low')} / {None if not pair else pair.get('ci_high')}")
    gate('Regime coverage',covered>=int(min_regimes),f'{covered} regimes with n>=5')
    gate('Persistence',persistence.get('state')=='PERSISTENT',str(persistence.get('state') or 'OBSERVE'))
    gate('Multi-horizon maturity',bool(tr and tr.get('status')=='MATURE' and int(tr.get('supported_horizons') or 0)>=2),f"{None if not tr else tr.get('supported_horizons')} supported horizons")
    gate('Utility drawdown',maxdd<=float(max_utility_drawdown),f'{maxdd:.2f} <= {max_utility_drawdown:.2f}')
    gate('Missed-opportunity rate',miss_rate<=float(max_miss_rate_pct),f'{miss_rate:.1f}% <= {max_miss_rate_pct:.1f}%')
    reasons=[g['name'] for g in gates if g['hard'] and not g['pass']]
    status='PROMOTION_REVIEW' if not reasons else 'OBSERVE'
    return {'status':status,'version':'92.0','policy_id':policy_id,'horizon':horizon,'reasons':reasons,'gates':gates,
            'metrics':{'forward_span_days':round(span_days,2),'settled_signals':len(rows),'selected_signals':len(selected),
                       'regime_counts':regime_counts,'covered_regimes':covered,'utility_max_drawdown_pct_points':round(maxdd,3),
                       'missed_good_n':missed,'no_trade_n':len(no_trade),'miss_rate_pct':round(miss_rate,2)},
            'live_execution':False,
            'policy':'Promotion review only. Historical backtests cannot satisfy these gates; no policy is activated or sent to live execution automatically.'}

def report():
    rows=[evaluate(pid) for pid in ['strict','adaptive']]
    return {'status':'OK','version':'92.0','rows':rows,'review_candidates':[x for x in rows if x['status']=='PROMOTION_REVIEW'],
            'live_execution':False,'policy':'Forward-only policy promotion governance.'}
