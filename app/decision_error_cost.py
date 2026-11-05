"""V95 prospective decision error-cost matrix.
Separates false-positive downside from false-negative missed upside using settled benchmark excess.
Neutral outcomes stay neutral instead of being forced into binary accuracy.
"""
from __future__ import annotations
from . import experience_engine as ex

def analyze(horizon=20,good_excess_pct=3.0,bad_excess_pct=-3.0,false_positive_weight=1.0,false_negative_weight=1.0):
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    good=max(.1,float(good_excess_pct));bad=min(-.1,float(bad_excess_pct))
    with ex._LOCK:
        c=ex._conn();c.row_factory=__import__('sqlite3').Row
        rows=[dict(x) for x in c.execute(f'''SELECT id,ticker,committee_decision,regime,excess_{horizon} AS excess
          FROM signals WHERE settled_{horizon}=1 AND excess_{horizon} IS NOT NULL ORDER BY id''').fetchall()]
        c.close()
    buckets={'TP':[],'TN':[],'FP':[],'FN':[],'NEUTRAL_SELECTED':[],'NEUTRAL_REJECTED':[]}
    for r in rows:
        x=float(r['excess']);selected=r.get('committee_decision') in {'PASS','WATCH'}
        if x>=good:b='TP' if selected else 'FN'
        elif x<=bad:b='FP' if selected else 'TN'
        else:b='NEUTRAL_SELECTED' if selected else 'NEUTRAL_REJECTED'
        buckets[b].append({'id':r['id'],'ticker':r['ticker'],'decision':r.get('committee_decision'),'regime':r.get('regime'),'excess':round(x,3)})
    fp_cost=sum(abs(x['excess']) for x in buckets['FP'])
    fn_cost=sum(x['excess'] for x in buckets['FN'])
    weighted_fp=fp_cost*max(0,float(false_positive_weight))
    weighted_fn=fn_cost*max(0,float(false_negative_weight))
    total_error=weighted_fp+weighted_fn
    decisive=sum(len(buckets[k]) for k in ['TP','TN','FP','FN'])
    correct=len(buckets['TP'])+len(buckets['TN'])
    return {'status':'OK','version':'95.0','horizon':horizon,'good_threshold_pct':good,'bad_threshold_pct':bad,
            'settled_signals':len(rows),'decisive_signals':decisive,
            'accuracy_pct':round(correct/max(1,decisive)*100,2),
            'matrix':{k:{'n':len(v),'examples':v[-20:]} for k,v in buckets.items()},
            'costs':{'false_positive_downside_sum_pct':round(fp_cost,3),'false_negative_missed_upside_sum_pct':round(fn_cost,3),
                     'false_positive_weight':float(false_positive_weight),'false_negative_weight':float(false_negative_weight),
                     'weighted_false_positive_cost':round(weighted_fp,3),'weighted_false_negative_cost':round(weighted_fn,3),
                     'total_weighted_error_cost':round(total_error,3),
                     'dominant_error':'FALSE_POSITIVE' if weighted_fp>weighted_fn else 'FALSE_NEGATIVE' if weighted_fn>weighted_fp else 'BALANCED'},
            'live_execution':False,
            'policy':'Prospective diagnostic only. Error costs use benchmark-excess percentage points, not realized cash PnL; neutral outcomes are excluded from binary accuracy.'}
