"""V93 prospective gate-threshold challenger lab.
Each variant changes only one threshold while keeping all other incumbent committee gates fixed.
No historical backfill and no automatic threshold mutation.
"""
from __future__ import annotations
import json,sqlite3,time
from . import experience_engine as ex

VARIANTS=[
 {'id':'guard_50','gate':'Sinyal Kontrolü','field':'guard_score','op':'lt','threshold':50.0},
 {'id':'guard_60','gate':'Sinyal Kontrolü','field':'guard_score','op':'lt','threshold':60.0},
 {'id':'guard_65','gate':'Sinyal Kontrolü','field':'guard_score','op':'lt','threshold':65.0},
 {'id':'guard_70','gate':'Sinyal Kontrolü','field':'guard_score','op':'lt','threshold':70.0},
 {'id':'trap_50','gate':'Tuzak Savunması','field':'trap_score','op':'lt','threshold':50.0},
 {'id':'trap_60','gate':'Tuzak Savunması','field':'trap_score','op':'lt','threshold':60.0},
 {'id':'trap_65','gate':'Tuzak Savunması','field':'trap_score','op':'lt','threshold':65.0},
 {'id':'trap_70','gate':'Tuzak Savunması','field':'trap_score','op':'lt','threshold':70.0},
 {'id':'risk_75','gate':'Aşırı risk yok','field':'risk','op':'lt','threshold':75.0},
 {'id':'risk_82','gate':'Aşırı risk yok','field':'risk','op':'lt','threshold':82.0},
 {'id':'risk_88','gate':'Aşırı risk yok','field':'risk','op':'lt','threshold':88.0},
 {'id':'anomaly_80','gate':'Anomali proxy aşırı değil','field':'anomaly','op':'lt','threshold':80.0},
 {'id':'anomaly_90','gate':'Anomali proxy aşırı değil','field':'anomaly','op':'lt','threshold':90.0},
 {'id':'anomaly_95','gate':'Anomali proxy aşırı değil','field':'anomaly','op':'lt','threshold':95.0},
]

def _ensure(c):
    c.execute('''CREATE TABLE IF NOT EXISTS gate_threshold_shadow(
      signal_id INTEGER, variant_id TEXT, gate_name TEXT, threshold REAL, passed INTEGER,
      committee_decision TEXT, created_epoch REAL, PRIMARY KEY(signal_id,variant_id)
    )''');c.commit()

def _passes(v,inputs):
    x=inputs.get(v['field'])
    try:x=float(x)
    except Exception:return False
    if v['field']=='guard_score' and str(inputs.get('guard_status') or '')!='CLEAR':return False
    if v['field']=='trap_score' and str(inputs.get('trap_status') or '')=='BLOCK':return False
    return x<float(v['threshold'])

def record(signal_id,committee,max_signal_age_sec=120):
    if not signal_id or not committee:return {'status':'SKIP','recorded':0}
    inputs=(committee or {}).get('decision_inputs') or {}
    gates=(committee or {}).get('gates') or []
    with ex._LOCK:
        c=ex._conn();_ensure(c)
        row=c.execute('SELECT created_epoch FROM signals WHERE id=?',(int(signal_id),)).fetchone()
        if not row or time.time()-float(row[0])>float(max_signal_age_sec):
            c.close();return {'status':'STALE_SIGNAL_ID','recorded':0}
        n=0
        for v in VARIANTS:
            other_hard_fail=any(g.get('hard') and not g.get('pass') and g.get('name')!=v['gate'] for g in gates)
            passed=_passes(v,inputs)
            decision='NO_TRADE' if other_hard_fail or not passed else str((committee or {}).get('decision') or 'NO_TRADE')
            cur=c.execute('INSERT OR IGNORE INTO gate_threshold_shadow(signal_id,variant_id,gate_name,threshold,passed,committee_decision,created_epoch) VALUES(?,?,?,?,?,?,?)',
                          (int(signal_id),v['id'],v['gate'],float(v['threshold']),int(passed),decision,time.time()))
            n+=cur.rowcount
        c.commit();c.close()
    return {'status':'OK','recorded':n}

def report(horizon=20,min_settled=12):
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    with ex._LOCK:
        c=ex._conn();_ensure(c);c.row_factory=sqlite3.Row
        rows=[dict(x) for x in c.execute(f'''SELECT g.variant_id,g.gate_name,g.threshold,g.passed,g.committee_decision,
          s.excess_{horizon} AS excess
          FROM gate_threshold_shadow g JOIN signals s ON s.id=g.signal_id
          WHERE s.settled_{horizon}=1 AND s.excess_{horizon} IS NOT NULL
          ORDER BY g.signal_id''').fetchall()];c.close()
    out=[]
    for v in VARIANTS:
        vr=[r for r in rows if r['variant_id']==v['id']]
        passx=[float(r['excess']) for r in vr if r['passed']]
        failx=[float(r['excess']) for r in vr if not r['passed']]
        delta=(sum(passx)/len(passx)-sum(failx)/len(failx)) if passx and failx else None
        protected=sum(1 for x in failx if x<=-3);missed=sum(1 for x in failx if x>=3)
        status='MATURE' if len(vr)>=int(min_settled) and len(passx)>=4 and len(failx)>=4 else 'OBSERVE'
        out.append({'id':v['id'],'gate':v['gate'],'threshold':v['threshold'],'status':status,'settled_n':len(vr),
                    'pass_n':len(passx),'fail_n':len(failx),'pass_mean_excess_pct':None if not passx else round(sum(passx)/len(passx),3),
                    'fail_mean_excess_pct':None if not failx else round(sum(failx)/len(failx),3),
                    'delta_pass_minus_fail_pct':None if delta is None else round(delta,3),
                    'protected_bad_n':protected,'missed_good_n':missed})
    groups={}
    for r in out:groups.setdefault(r['gate'],[]).append(r)
    leaders=[]
    for gate,items in groups.items():
        mature=[x for x in items if x['status']=='MATURE' and x['delta_pass_minus_fail_pct'] is not None]
        if mature:
            best=max(mature,key=lambda x:(x['delta_pass_minus_fail_pct'],x['protected_bad_n']-x['missed_good_n']))
            leaders.append({'gate':gate,'variant_id':best['id'],'threshold':best['threshold'],'delta':best['delta_pass_minus_fail_pct']})
    return {'status':'OK','version':'93.0','horizon':horizon,'rows':out,'leaders':leaders,'live_execution':False,
            'policy':'Prospective threshold shadow lab only. Leaders are research observations; thresholds are never changed automatically and historical backfill is forbidden.'}
