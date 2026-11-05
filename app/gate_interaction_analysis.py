"""V94 forward-only gate interaction analysis.
Measures co-failure overlap and settled outcome associations for hard-gate pairs.
Association is diagnostic, not causal, and never removes gates automatically.
"""
from __future__ import annotations
import json,itertools,statistics
from . import experience_engine as ex

def _mean(xs):
    return sum(xs)/len(xs) if xs else None

def analyze(horizon=20,min_samples=6):
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    with ex._LOCK:
        c=ex._conn();c.row_factory=__import__('sqlite3').Row
        rows=[dict(x) for x in c.execute(f'''SELECT id,setup_json,excess_{horizon} AS excess
          FROM signals WHERE settled_{horizon}=1 AND excess_{horizon} IS NOT NULL ORDER BY id''').fetchall()]
        c.close()
    parsed=[]
    names=set()
    for r in rows:
        try:setup=json.loads(r.get('setup_json') or '{}')
        except Exception:setup={}
        gates=[g for g in (setup.get('committee_gates') or []) if g.get('hard') and g.get('name')]
        state={str(g['name']):bool(g.get('pass')) for g in gates};names.update(state)
        parsed.append((float(r['excess']),state))
    out=[]
    for a,b in itertools.combinations(sorted(names),2):
        af=[];bf=[];both=[];a_only=[];b_only=[];neither=[]
        for exv,state in parsed:
            if a not in state or b not in state:continue
            fa=not state[a];fb=not state[b]
            if fa:af.append(exv)
            if fb:bf.append(exv)
            if fa and fb:both.append(exv)
            elif fa:a_only.append(exv)
            elif fb:b_only.append(exv)
            else:neither.append(exv)
        union=len(af)+len(bf)-len(both)
        jaccard=len(both)/union if union else 0.0
        singles=a_only+b_only
        interaction=None if not both or not singles else _mean(both)-_mean(singles)
        both_mean=_mean(both)
        if len(both)<int(min_samples):label='INSUFFICIENT'
        elif jaccard>=.70:label='REDUNDANCY_REVIEW'
        elif both_mean is not None and both_mean<=-3 and interaction is not None and interaction<=-1:label='JOINT_PROTECTIVE'
        elif both_mean is not None and both_mean>=3:label='JOINT_COSTLY'
        else:label='MONITOR'
        out.append({'gate_a':a,'gate_b':b,'pair':a+' + '+b,'both_fail_n':len(both),'a_fail_n':len(af),'b_fail_n':len(bf),
                    'a_only_n':len(a_only),'b_only_n':len(b_only),'neither_n':len(neither),
                    'failure_jaccard_pct':round(jaccard*100,2),
                    'both_fail_mean_excess_pct':None if both_mean is None else round(both_mean,3),
                    'single_fail_mean_excess_pct':None if not singles else round(_mean(singles),3),
                    'interaction_delta_pct':None if interaction is None else round(interaction,3),'label':label})
    order={'REDUNDANCY_REVIEW':0,'JOINT_COSTLY':1,'JOINT_PROTECTIVE':2,'MONITOR':3,'INSUFFICIENT':4}
    out.sort(key=lambda x:(order.get(x['label'],9),-x['both_fail_n'],-x['failure_jaccard_pct'],x['pair']))
    return {'status':'OK','version':'94.0','horizon':horizon,'settled_signals':len(rows),'rows':out,
            'redundancy_candidates':[x for x in out if x['label']=='REDUNDANCY_REVIEW'],
            'joint_protective':[x for x in out if x['label']=='JOINT_PROTECTIVE'],
            'joint_costly':[x for x in out if x['label']=='JOINT_COSTLY'],
            'policy':'Forward association diagnostic only. High overlap can indicate redundant evidence, shared cause or regime dependence; no gate is removed or weakened automatically.'}
