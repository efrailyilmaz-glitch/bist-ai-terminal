"""V84 forward-only committee gate calibration.
Measures associations between gate pass/fail states and settled future excess returns.
No causal claims and no automatic threshold mutation.
"""
from __future__ import annotations
import json,math,hashlib
import numpy as np
from . import experience_engine as ex

def _f(x):
    try:
        z=float(x);return z if math.isfinite(z) else None
    except Exception:return None

def _boot_delta(a,b,simulations=3000,seed=84):
    a=np.asarray([float(x) for x in a if _f(x) is not None],float)
    b=np.asarray([float(x) for x in b if _f(x) is not None],float)
    if len(a)<2 or len(b)<2:return None
    rng=np.random.default_rng(seed)
    sims=max(1000,min(int(simulations),10000));d=np.empty(sims,float)
    for i in range(sims):
        d[i]=rng.choice(a,size=len(a),replace=True).mean()-rng.choice(b,size=len(b),replace=True).mean()
    return {'ci_low':float(np.quantile(d,.025)),'ci_high':float(np.quantile(d,.975)),
            'prob_positive':float(np.mean(d>0)),'simulations':sims}

def _seed(name,horizon):
    return int(hashlib.sha256((str(name)+'|'+str(horizon)).encode()).hexdigest()[:8],16)

def gate_calibration(horizon=20,min_samples=8,simulations=3000):
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    with ex._LOCK:
        c=ex._conn();c.row_factory=__import__('sqlite3').Row
        rows=[dict(x) for x in c.execute(f'''SELECT id,ticker,committee_decision,regime,setup_json,excess_{horizon} AS excess
                                             FROM signals
                                             WHERE settled_{horizon}=1 AND excess_{horizon} IS NOT NULL
                                             ORDER BY id''').fetchall()]
        c.close()
    parsed=[]
    for r in rows:
        try:setup=json.loads(r.get('setup_json') or '{}')
        except Exception:setup={}
        gates=setup.get('committee_gates') or []
        parsed.append((r,gates))
    names=sorted({str(g.get('name')) for _,gs in parsed for g in gs if g.get('name')})
    out=[]
    for name in names:
        passed=[];failed=[];hard=None
        for r,gs in parsed:
            g=next((x for x in gs if str(x.get('name'))==name),None)
            if not g:continue
            hard=bool(g.get('hard')) if hard is None else hard
            (passed if g.get('pass') else failed).append(float(r['excess']))
        delta=None;boot=None
        if len(passed)>=min_samples and len(failed)>=min_samples:
            delta=float(np.mean(passed)-np.mean(failed));boot=_boot_delta(passed,failed,simulations,_seed(name,horizon))
        if boot is None:label='INSUFFICIENT'
        elif boot['ci_low']>0 and delta>=.5:label='USEFUL'
        elif boot['ci_high']<0 and delta<=-.5:label='REVIEW_TOO_STRICT'
        else:label='MONITOR'
        out.append({'gate':name,'hard':bool(hard),'pass_n':len(passed),'fail_n':len(failed),
                    'pass_mean_excess_pct':None if not passed else round(float(np.mean(passed)),3),
                    'fail_mean_excess_pct':None if not failed else round(float(np.mean(failed)),3),
                    'delta_pass_minus_fail_pct':None if delta is None else round(delta,3),
                    'delta_ci_low':None if not boot else round(boot['ci_low'],3),
                    'delta_ci_high':None if not boot else round(boot['ci_high'],3),
                    'prob_delta_positive_pct':None if not boot else round(boot['prob_positive']*100,2),
                    'label':label})
    order={'REVIEW_TOO_STRICT':0,'USEFUL':1,'MONITOR':2,'INSUFFICIENT':3}
    out.sort(key=lambda x:(order.get(x['label'],9),-(abs(x['delta_pass_minus_fail_pct']) if x['delta_pass_minus_fail_pct'] is not None else -1),x['gate']))
    return {'status':'OK','version':'84.0','horizon':horizon,'settled_signals':len(rows),'min_samples_per_side':int(min_samples),
            'rows':out,'review_candidates':[x for x in out if x['label']=='REVIEW_TOO_STRICT'],
            'useful_gates':[x for x in out if x['label']=='USEFUL'],
            'policy':'Forward-only association diagnostic. A gate is never weakened or removed automatically; all threshold changes require separate prospective validation.'}

def decision_calibration():
    return {'5d':gate_calibration(5),'20d':gate_calibration(20),'60d':gate_calibration(60)}
