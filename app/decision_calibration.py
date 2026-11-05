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


def missed_opportunity_audit(horizon=20,min_excess_pct=3.0,min_samples=3):
    """Audit prospective NO_TRADE records that later materially outperformed the benchmark.
    This is a false-negative diagnostic, not a claim that a trade should have been executed.
    """
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    with ex._LOCK:
        c=ex._conn();c.row_factory=__import__('sqlite3').Row
        rows=[dict(x) for x in c.execute(f'''SELECT id,ticker,created_at,committee_score,regime,setup_json,ret_{horizon} AS ret,excess_{horizon} AS excess
                                             FROM signals
                                             WHERE committee_decision='NO_TRADE'
                                               AND settled_{horizon}=1 AND excess_{horizon} IS NOT NULL
                                             ORDER BY id DESC''').fetchall()]
        c.close()
    misses=[];by_gate={}
    threshold=float(min_excess_pct)
    for r in rows:
        exv=float(r.get('excess') or 0)
        if exv<threshold:continue
        try:setup=json.loads(r.get('setup_json') or '{}')
        except Exception:setup={}
        failed=[g for g in (setup.get('committee_gates') or []) if g.get('hard') and not g.get('pass')]
        vetoes=list(setup.get('vetoes') or [])
        names=list(dict.fromkeys([str(g.get('name')) for g in failed if g.get('name')]+[str(x) for x in vetoes if x]))
        item={'id':r['id'],'ticker':r['ticker'],'created_at':r.get('created_at'),'committee_score':r.get('committee_score'),
              'regime':r.get('regime'),'return_pct':round(float(r.get('ret') or 0),3),'excess_pct':round(exv,3),
              'failed_hard_gates':names}
        misses.append(item)
        for name in names:
            z=by_gate.setdefault(name,{'gate':name,'misses':0,'excess_values':[],'tickers':[]})
            z['misses']+=1;z['excess_values'].append(exv);z['tickers'].append(r['ticker'])
    gates=[]
    for z in by_gate.values():
        vals=z.pop('excess_values')
        z['mean_missed_excess_pct']=round(float(np.mean(vals)),3) if vals else None
        z['max_missed_excess_pct']=round(float(np.max(vals)),3) if vals else None
        z['unique_tickers']=len(set(z.pop('tickers')))
        z['review']=z['misses']>=int(min_samples)
        gates.append(z)
    gates.sort(key=lambda x:(not x['review'],-x['misses'],-(x['mean_missed_excess_pct'] or 0),x['gate']))
    return {'status':'OK','version':'85.0','horizon':horizon,'threshold_excess_pct':threshold,
            'settled_no_trade':len(rows),'missed_opportunities':len(misses),
            'miss_rate_pct':round(len(misses)/max(1,len(rows))*100,2),
            'gate_summary':gates,'recent_misses':misses[:100],
            'policy':'Forward false-negative audit only. A missed opportunity does not prove the veto was wrong; risk avoided by vetoes is analyzed separately and no gate is auto-disabled.'}


def gate_net_utility(horizon=20,bad_excess_pct=-3.0,good_excess_pct=3.0,min_samples=8):
    """Balance downside avoided vs upside missed for each failed hard gate using settled prospective evidence.
    Multiple failed gates may share the same outcome; scores are diagnostic associations, not causal PnL attribution.
    """
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    bad=float(bad_excess_pct);good=float(good_excess_pct)
    if bad>=0:bad=-abs(bad or 3.0)
    if good<=0:good=abs(good or 3.0)
    with ex._LOCK:
        c=ex._conn();c.row_factory=__import__('sqlite3').Row
        rows=[dict(x) for x in c.execute(f'''SELECT id,ticker,committee_decision,regime,setup_json,excess_{horizon} AS excess
                                             FROM signals
                                             WHERE settled_{horizon}=1 AND excess_{horizon} IS NOT NULL
                                             ORDER BY id''').fetchall()]
        c.close()
    by_gate={}
    for r in rows:
        try:setup=json.loads(r.get('setup_json') or '{}')
        except Exception:setup={}
        failed=[g for g in (setup.get('committee_gates') or []) if g.get('hard') and not g.get('pass') and g.get('name')]
        exv=float(r.get('excess') or 0)
        for g in failed:
            name=str(g['name'])
            z=by_gate.setdefault(name,{'gate':name,'failed_n':0,'bad':[],'good':[],'neutral':[],'all':[],'regimes':{}})
            z['failed_n']+=1;z['all'].append(exv)
            bucket='bad' if exv<=bad else 'good' if exv>=good else 'neutral'
            z[bucket].append(exv)
            reg=str(r.get('regime') or 'UNKNOWN').upper()
            rr=z['regimes'].setdefault(reg,{'n':0,'bad_n':0,'good_n':0})
            rr['n']+=1;rr['bad_n']+=int(bucket=='bad');rr['good_n']+=int(bucket=='good')
    out=[]
    for z in by_gate.values():
        n=z['failed_n'];bad_vals=z['bad'];good_vals=z['good'];neutral=z['neutral'];all_vals=z.pop('all')
        avoided_loss=sum(abs(x) for x in bad_vals)
        missed_upside=sum(x for x in good_vals)
        gross=avoided_loss-missed_upside
        avg=gross/max(1,n)
        protection_rate=len(bad_vals)/max(1,n)*100
        miss_rate=len(good_vals)/max(1,n)*100
        if n<int(min_samples):label='INSUFFICIENT'
        elif avg>=1.0 and protection_rate>miss_rate:label='NET_PROTECTIVE'
        elif avg<=-1.0 and miss_rate>protection_rate:label='NET_COSTLY'
        else:label='BALANCED'
        out.append({'gate':z['gate'],'failed_n':n,'bad_n':len(bad_vals),'good_n':len(good_vals),'neutral_n':len(neutral),
                    'protection_rate_pct':round(protection_rate,2),'miss_rate_pct':round(miss_rate,2),
                    'avoided_downside_sum_pct':round(avoided_loss,3),'missed_upside_sum_pct':round(missed_upside,3),
                    'net_utility_sum_pct':round(gross,3),'net_utility_per_failure_pct':round(avg,3),
                    'failed_mean_excess_pct':round(float(np.mean(all_vals)),3) if all_vals else None,
                    'label':label,'regimes':z['regimes']})
    order={'NET_COSTLY':0,'NET_PROTECTIVE':1,'BALANCED':2,'INSUFFICIENT':3}
    out.sort(key=lambda x:(order.get(x['label'],9),x['net_utility_per_failure_pct'],x['gate']))
    return {'status':'OK','version':'86.0','horizon':horizon,'bad_excess_threshold_pct':bad,'good_excess_threshold_pct':good,
            'settled_signals':len(rows),'min_samples':int(min_samples),'rows':out,
            'review_candidates':[x for x in out if x['label']=='NET_COSTLY'],
            'protective_gates':[x for x in out if x['label']=='NET_PROTECTIVE'],
            'policy':'Prospective diagnostic only. Outcomes can be shared across simultaneous gate failures, so utility is not causal attribution and never changes a gate automatically.'}


def gate_regime_utility(horizon=20,bad_excess_pct=-3.0,good_excess_pct=3.0,min_samples=5):
    """Regime-sliced hard-gate utility from settled prospective outcomes.
    Intended to detect sign reversals hidden by aggregate averages.
    """
    base=gate_net_utility(horizon,bad_excess_pct,good_excess_pct,min_samples=2)
    rows=[]
    for g in base.get('rows') or []:
        for regime,rg in (g.get('regimes') or {}).items():
            n=int(rg.get('n') or 0);bad_n=int(rg.get('bad_n') or 0);good_n=int(rg.get('good_n') or 0)
            protect=bad_n/max(1,n)*100;miss=good_n/max(1,n)*100
            if n<int(min_samples):label='INSUFFICIENT'
            elif protect>=miss+15:label='PROTECTIVE'
            elif miss>=protect+15:label='COSTLY'
            else:label='MIXED'
            rows.append({'gate':g['gate'],'regime':regime,'n':n,'bad_n':bad_n,'good_n':good_n,
                         'protection_rate_pct':round(protect,2),'miss_rate_pct':round(miss,2),'label':label})
    conflicts=[]
    for gate in sorted({x['gate'] for x in rows}):
        labs={x['label'] for x in rows if x['gate']==gate and x['label']!='INSUFFICIENT'}
        if 'PROTECTIVE' in labs and 'COSTLY' in labs:conflicts.append(gate)
    order={'COSTLY':0,'PROTECTIVE':1,'MIXED':2,'INSUFFICIENT':3}
    rows.sort(key=lambda x:(order.get(x['label'],9),x['gate'],x['regime']))
    return {'status':'OK','version':'87.0','horizon':horizon,'rows':rows,'regime_conflict_gates':conflicts,
            'policy':'Regime-sliced prospective diagnostic. Regime conflict triggers review only; no regime-specific gate relaxation is automatic.'}
