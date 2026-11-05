"""V88 forward-only shadow decision policy challengers.
Policies are evaluated only at signal-record time from the same committee snapshot.
They never alter the incumbent committee decision or authorize execution.
"""
from __future__ import annotations
import json,sqlite3,time,hashlib
import numpy as np
from . import experience_engine as ex

POLICIES=[
 {'id':'incumbent','name':'Incumbent','guard_max':65,'trap_max':60,'pass_score':80,'watch_score':68,'min_rr':1.5,'min_sample':15},
 {'id':'strict','name':'Strict Defense','guard_max':50,'trap_max':50,'pass_score':84,'watch_score':72,'min_rr':1.7,'min_sample':20},
 {'id':'adaptive','name':'Adaptive Challenger','guard_max':65,'trap_max':70,'pass_score':76,'watch_score':64,'min_rr':1.3,'min_sample':12},
]
IMMUTABLE_HARD={'Point-in-Time bütünlüğü','KAP tarih bütünlüğü','Likidite','Aşırı risk yok','Anomali proxy aşırı değil','Uzun trend bozuk değil','Bilanço stres veto'}

def _ensure(c):
    c.execute('''CREATE TABLE IF NOT EXISTS policy_shadow(
      signal_id INTEGER, policy_id TEXT, policy_name TEXT, decision TEXT, reasons_json TEXT,
      created_epoch REAL, PRIMARY KEY(signal_id,policy_id)
    )''')
    c.commit()

def _num(x,d=None):
    try:return float(x)
    except Exception:return d

def evaluate_snapshot(committee,policy):
    c=committee or {};gates=c.get('gates') or []
    failed_immutable=[g.get('name') for g in gates if g.get('hard') and not g.get('pass') and g.get('name') in IMMUTABLE_HARD]
    guard=c.get('signal_guard') or {};trap=c.get('trap_defense') or {}
    reasons=list(failed_immutable)
    guard_score=_num(guard.get('score'),100);trap_score=_num(trap.get('score'),100)
    if guard.get('status')!='CLEAR' or guard_score>=float(policy['guard_max']):reasons.append('SIGNAL_GUARD')
    if trap.get('status')=='BLOCK' or trap_score>=float(policy['trap_max']):reasons.append('TRAP_DEFENSE')
    score=_num(c.get('committee_score'),0);ev=_num(c.get('expected_value_pct'),-999);rr=_num(c.get('risk_reward'))
    sample=int(((c.get('empirical') or {}).get('sample') or 0))
    if reasons:decision='NO_TRADE'
    elif score>=policy['pass_score'] and ev>0 and (rr is None or rr>=policy['min_rr']) and sample>=policy['min_sample']:decision='PASS'
    elif score>=policy['watch_score'] and ev>=0:decision='WATCH'
    else:decision='NO_TRADE'
    return {'decision':decision,'reasons':list(dict.fromkeys(reasons)),
            'policy':policy,'snapshot':{'committee_score':score,'expected_value_pct':ev,'risk_reward':rr,'sample':sample,
                                       'guard_status':guard.get('status'),'guard_score':guard_score,
                                       'trap_status':trap.get('status'),'trap_score':trap_score}}

def record(signal_id,committee,max_signal_age_sec=120):
    if not signal_id or not committee:return {'recorded':0,'status':'SKIP'}
    with ex._LOCK:
        c=ex._conn();_ensure(c);n=0
        row=c.execute('SELECT created_epoch FROM signals WHERE id=?',(int(signal_id),)).fetchone()
        if not row or time.time()-float(row[0])>float(max_signal_age_sec):
            c.close();return {'recorded':0,'status':'STALE_SIGNAL_ID'}
        for p in POLICIES:
            r=evaluate_snapshot(committee,p)
            cur=c.execute('INSERT OR IGNORE INTO policy_shadow(signal_id,policy_id,policy_name,decision,reasons_json,created_epoch) VALUES(?,?,?,?,?,?)',
                          (int(signal_id),p['id'],p['name'],r['decision'],json.dumps(r,ensure_ascii=False,sort_keys=True),time.time()))
            n+=cur.rowcount
        c.commit();c.close()
    return {'recorded':n,'status':'OK'}

def _decision_utility(decision,excess):
    x=float(excess)
    return x if decision in {'PASS','WATCH'} else -x

def _paired_bootstrap(deltas,seed=89,simulations=5000):
    a=np.asarray([float(x) for x in deltas],float)
    if len(a)<8:return {'status':'INSUFFICIENT','n':len(a)}
    rng=np.random.default_rng(int(seed));sims=max(1000,min(int(simulations),10000))
    means=np.empty(sims,float)
    for i in range(sims):means[i]=rng.choice(a,size=len(a),replace=True).mean()
    return {'status':'OK','n':len(a),'mean_delta':float(a.mean()),
            'ci_low':float(np.quantile(means,.025)),'ci_high':float(np.quantile(means,.975)),
            'prob_positive':float(np.mean(means>0)),'simulations':sims}

def _paired_comparisons(rows,min_pairs=12):
    by_signal={}
    for r in rows:
        by_signal.setdefault(int(r['signal_id']),{})[r['policy_id']]=r
    out=[]
    for p in POLICIES:
        if p['id']=='incumbent':continue
        pairs=[];regimes={}
        for sid,d in by_signal.items():
            a=d.get('incumbent');b=d.get(p['id'])
            if not a or not b:continue
            inc=_decision_utility(a['decision'],a['excess']);chal=_decision_utility(b['decision'],b['excess'])
            delta=chal-inc;reg=str(a.get('regime') or 'UNKNOWN').upper()
            pairs.append(delta);regimes.setdefault(reg,[]).append(delta)
        boot=_paired_bootstrap(pairs,seed=int(hashlib.sha256(p['id'].encode()).hexdigest()[:8],16))
        reg_rows=[]
        for reg,vals in sorted(regimes.items()):
            rb=_paired_bootstrap(vals,seed=int(hashlib.sha256((p['id']+'|'+reg).encode()).hexdigest()[:8],16),simulations=3000)
            reg_rows.append({'regime':reg,'n':len(vals),'mean_delta':None if not vals else round(float(np.mean(vals)),3),
                             'ci_low':None if rb.get('status')!='OK' else round(rb['ci_low'],3),
                             'ci_high':None if rb.get('status')!='OK' else round(rb['ci_high'],3)})
        mature=len(pairs)>=int(min_pairs) and boot.get('status')=='OK'
        supportive=mature and boot['ci_low']>0 and boot['prob_positive']>=.95
        out.append({'challenger':p['id'],'name':p['name'],'paired_n':len(pairs),
                    'mean_utility_delta':None if boot.get('status')!='OK' else round(boot['mean_delta'],3),
                    'ci_low':None if boot.get('status')!='OK' else round(boot['ci_low'],3),
                    'ci_high':None if boot.get('status')!='OK' else round(boot['ci_high'],3),
                    'prob_positive_pct':None if boot.get('status')!='OK' else round(boot['prob_positive']*100,2),
                    'status':'SUPPORTED' if supportive else 'MATURE_NO_EDGE' if mature else 'OBSERVE',
                    'regimes':reg_rows})
    return out

def report(horizon=20,min_settled=12):
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    with ex._LOCK:
        c=ex._conn();_ensure(c);c.row_factory=sqlite3.Row
        rows=[dict(x) for x in c.execute(f'''SELECT p.signal_id,p.policy_id,p.policy_name,p.decision,s.regime,s.excess_{horizon} AS excess
          FROM policy_shadow p JOIN signals s ON s.id=p.signal_id
          WHERE s.settled_{horizon}=1 AND s.excess_{horizon} IS NOT NULL ORDER BY p.signal_id''').fetchall()]
        c.close()
    out=[]
    for p in POLICIES:
        pr=[r for r in rows if r['policy_id']==p['id']]
        passx=[float(r['excess']) for r in pr if r['decision']=='PASS']
        watchx=[float(r['excess']) for r in pr if r['decision']=='WATCH']
        nox=[float(r['excess']) for r in pr if r['decision']=='NO_TRADE']
        selected=passx+watchx
        n=len(pr);sel=len(selected)
        mean=sum(selected)/len(selected) if selected else None
        hit=sum(1 for x in selected if x>0)/len(selected)*100 if selected else None
        missed=sum(1 for x in nox if x>=3)
        protected=sum(1 for x in nox if x<=-3)
        score=(mean or 0)+0.04*((hit or 50)-50)+0.15*(protected-missed)/max(1,n)*100
        status='MATURE' if n>=int(min_settled) and sel>=5 else 'OBSERVE'
        out.append({'id':p['id'],'name':p['name'],'status':status,'settled_n':n,'selected_n':sel,
                    'pass_n':len(passx),'watch_n':len(watchx),'no_trade_n':len(nox),
                    'selected_mean_excess_pct':None if mean is None else round(mean,3),
                    'selected_hit_rate_pct':None if hit is None else round(hit,2),
                    'protected_bad_n':protected,'missed_good_n':missed,'shadow_score':round(score,3),'policy':p})
    out.sort(key=lambda x:(x['status']!='MATURE',-x['shadow_score'],x['id']))
    incumbent=next((x for x in out if x['id']=='incumbent'),None)
    paired=_paired_comparisons(rows,min_pairs=max(12,int(min_settled)))
    best=out[0] if out else None
    decision={'action':'HOLD','reason':'INSUFFICIENT_FORWARD_EVIDENCE'}
    if best and incumbent and best['id']!='incumbent' and best['status']=='MATURE' and incumbent['status']=='MATURE':
        pc=next((x for x in paired if x['challenger']==best['id']),None)
        margin=best['shadow_score']-incumbent['shadow_score']
        regime_ns=[int(x.get('n') or 0) for x in (pc or {}).get('regimes') or []]
        regime_ok=sum(1 for n in regime_ns if n>=5)>=2
        if margin>=1.5 and best['selected_n']>=10 and pc and pc['status']=='SUPPORTED' and regime_ok:
            decision={'action':'CHALLENGER_REVIEW','challenger':best['id'],'margin':round(margin,3),
                      'paired_mean_delta':pc.get('mean_utility_delta'),'reason':'PAIRED_FORWARD_EDGE_WITH_REGIME_COVERAGE'}
        elif pc and pc['status']!='SUPPORTED':
            decision={'action':'HOLD','reason':'PAIRED_EDGE_NOT_CONFIRMED'}
        elif not regime_ok:
            decision={'action':'HOLD','reason':'INSUFFICIENT_REGIME_COVERAGE'}
        else:decision={'action':'HOLD','reason':'NO_MATERIAL_MARGIN'}
    return {'status':'OK','version':'89.0','horizon':horizon,'rows':out,'paired_comparisons':paired,'decision':decision,
            'live_execution':False,'policy':'Shadow policies are prospective-only. Challenger review requires paired bootstrap evidence and regime coverage; it never mutates incumbent thresholds automatically.'}
