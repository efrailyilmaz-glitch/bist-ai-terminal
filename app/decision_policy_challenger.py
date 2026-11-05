"""V88 forward-only shadow decision policy challengers.
Policies are evaluated only at signal-record time from the same committee snapshot.
They never alter the incumbent committee decision or authorize execution.
"""
from __future__ import annotations
import json,sqlite3,time
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

def record(signal_id,committee):
    if not signal_id or not committee:return {'recorded':0}
    with ex._LOCK:
        c=ex._conn();_ensure(c);n=0
        for p in POLICIES:
            r=evaluate_snapshot(committee,p)
            cur=c.execute('INSERT OR IGNORE INTO policy_shadow(signal_id,policy_id,policy_name,decision,reasons_json,created_epoch) VALUES(?,?,?,?,?,?)',
                          (int(signal_id),p['id'],p['name'],r['decision'],json.dumps(r,ensure_ascii=False,sort_keys=True),time.time()))
            n+=cur.rowcount
        c.commit();c.close()
    return {'recorded':n}

def report(horizon=20,min_settled=12):
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    with ex._LOCK:
        c=ex._conn();_ensure(c);c.row_factory=sqlite3.Row
        rows=[dict(x) for x in c.execute(f'''SELECT p.policy_id,p.policy_name,p.decision,s.excess_{horizon} AS excess
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
    best=out[0] if out else None
    decision={'action':'HOLD','reason':'INSUFFICIENT_FORWARD_EVIDENCE'}
    if best and incumbent and best['id']!='incumbent' and best['status']=='MATURE' and incumbent['status']=='MATURE':
        margin=best['shadow_score']-incumbent['shadow_score']
        if margin>=1.5 and best['selected_n']>=10:
            decision={'action':'CHALLENGER_REVIEW','challenger':best['id'],'margin':round(margin,3),'reason':'FORWARD_SHADOW_MARGIN'}
        else:decision={'action':'HOLD','reason':'NO_MATERIAL_MARGIN'}
    return {'status':'OK','version':'88.0','horizon':horizon,'rows':out,'decision':decision,
            'live_execution':False,'policy':'Shadow policies are prospective-only. CHALLENGER_REVIEW is a human/research review state; it never mutates incumbent thresholds automatically.'}
