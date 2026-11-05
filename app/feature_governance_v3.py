"""V115 Feature Governance 3.0.
Adds prospective redundancy, decay and explicit lineage/leakage metadata controls on top of
V47/V71 governance. New features are research candidates only until registered with inspectable
point-in-time metadata and sufficient forward evidence. No alpha feature is auto-promoted.
"""
from __future__ import annotations
from contextlib import closing
import json,sqlite3,time,math
from pathlib import Path
from collections import defaultdict
from .runtime_db import connect as db_connect
from . import experience_engine as ex
from .decision_attribution import _feature_map, attribution
from .feature_governance import governance_report as legacy_governance
from .protected_feature_governance import is_protected

def _db():
    p=Path.home()/'.bist-ai-terminal'/'feature_registry_v3.db'
    p.parent.mkdir(parents=True,exist_ok=True);return p

def _conn():
    c=db_connect(_db())
    c.execute('''CREATE TABLE IF NOT EXISTS feature_registry(
      feature TEXT PRIMARY KEY, source TEXT, version TEXT, owner TEXT,
      point_in_time INTEGER, future_derived INTEGER, causality_status TEXT,
      schema_json TEXT, created_epoch REAL, updated_epoch REAL
    )''')
    c.commit();return c

def register(meta):
    m=meta or {};feature=str(m.get('feature') or '').strip()
    if not feature:return {'status':'ERROR','error':'feature is required'}
    pit=m.get('point_in_time') is True
    future=m.get('future_derived') is True
    causality=str(m.get('causality_status') or 'UNKNOWN').upper()
    source=str(m.get('source') or 'UNKNOWN');version=str(m.get('version') or 'UNVERSIONED')
    owner=str(m.get('owner') or 'RESEARCH')
    schema=m.get('schema') or {}
    now=time.time()
    with closing(_conn()) as c:
        prev=c.execute('SELECT created_epoch FROM feature_registry WHERE feature=?',(feature,)).fetchone()
        created=float(prev[0]) if prev else now
        c.execute('''INSERT OR REPLACE INTO feature_registry(feature,source,version,owner,point_in_time,future_derived,causality_status,schema_json,created_epoch,updated_epoch)
                     VALUES(?,?,?,?,?,?,?,?,?,?)''',
                  (feature,source,version,owner,int(pit),int(future),causality,json.dumps(schema,sort_keys=True,ensure_ascii=False),created,now))
    return {'status':'OK','feature':feature,'research_only':True,
            'note':'Registration records provenance only. It never promotes a feature to production/champion scoring.'}

def registry():
    with closing(_conn()) as c:
        c.row_factory=sqlite3.Row
        rows=[dict(x) for x in c.execute('SELECT * FROM feature_registry ORDER BY feature').fetchall()]
    for r in rows:
        try:r['schema']=json.loads(r.pop('schema_json') or '{}')
        except Exception:r['schema']={}
        r['point_in_time']=bool(r.get('point_in_time'));r['future_derived']=bool(r.get('future_derived'))
    return {'status':'OK','version':'115.0','rows':rows}

def _settled(horizon):
    with ex._LOCK:
        c=ex._conn();c.row_factory=sqlite3.Row
        rows=[dict(x) for x in c.execute(f'''SELECT id,created_epoch,regime,setup_json,excess_{horizon} AS excess
                                             FROM signals
                                             WHERE settled_{horizon}=1 AND excess_{horizon} IS NOT NULL
                                             ORDER BY created_epoch''').fetchall()]
        c.close()
    out=[]
    for r in rows:
        try:setup=json.loads(r.get('setup_json') or '{}')
        except Exception:setup={}
        out.append((r,_feature_map(setup)))
    return out

def _redundancy(parsed,min_joint=12):
    names=sorted({k for _,m in parsed for k in m})
    pairs=[]
    for i,a in enumerate(names):
        for b in names[i+1:]:
            na=nb=both=0
            for _,m in parsed:
                va=bool(m.get(a));vb=bool(m.get(b))
                na+=int(va);nb+=int(vb);both+=int(va and vb)
            union=na+nb-both
            if both<int(min_joint) or union<=0:continue
            j=both/union
            if j>=.75:
                pairs.append({'feature_a':a,'feature_b':b,'joint_n':both,'a_n':na,'b_n':nb,
                              'jaccard_pct':round(j*100,2),
                              'label':'HIGH_REDUNDANCY' if j>=.90 else 'REDUNDANCY_WATCH'})
    pairs.sort(key=lambda x:(-x['jaccard_pct'],-x['joint_n'],x['feature_a'],x['feature_b']))
    return pairs

def _decay(parsed,min_side=8):
    by=defaultdict(list)
    for r,m in parsed:
        for f in m:by[f].append((float(r['created_epoch']),float(r['excess'])))
    rows=[]
    for f,vals in by.items():
        vals=sorted(vals)
        if len(vals)<2*int(min_side):continue
        cut=len(vals)//2;early=[x[1] for x in vals[:cut]];recent=[x[1] for x in vals[cut:]]
        if len(early)<min_side or len(recent)<min_side:continue
        em=sum(early)/len(early);rm=sum(recent)/len(recent);delta=rm-em
        if em>0.5 and rm<=0:label='DECAY'
        elif delta<=-1.0:label='WEAKENING'
        elif em<0 and rm>0.5:label='RECOVERING'
        else:label='STABLE'
        rows.append({'feature':f,'n':len(vals),'early_n':len(early),'recent_n':len(recent),
                     'early_mean_excess_pct':round(em,3),'recent_mean_excess_pct':round(rm,3),
                     'recent_minus_early_pct':round(delta,3),'label':label})
    order={'DECAY':0,'WEAKENING':1,'RECOVERING':2,'STABLE':3}
    rows.sort(key=lambda x:(order.get(x['label'],9),x['recent_minus_early_pct'],x['feature']))
    return rows

def report(horizon=20,min_forward_n=30):
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    parsed=_settled(horizon);legacy=legacy_governance()
    attr=attribution(horizon,min_samples=12)
    reg={x['feature']:x for x in registry()['rows']}
    decay={x['feature']:x for x in _decay(parsed)}
    redundancy=_redundancy(parsed)
    redundant=defaultdict(list)
    for p in redundancy:
        redundant[p['feature_a']].append(p);redundant[p['feature_b']].append(p)
    legacy_rows={x.get('feature'):x for x in (legacy.get('rows') or [])}
    attr_rows={x.get('feature'):x for x in (attr.get('rows') or [])}
    features=sorted(set(legacy_rows)|set(attr_rows)|set(reg))
    rows=[]
    for f in features:
        lr=legacy_rows.get(f) or {};ar=attr_rows.get(f) or {};meta=reg.get(f)
        protected=is_protected(f)
        lineage=[]
        if meta is None:lineage.append('UNREGISTERED')
        else:
            if not meta.get('point_in_time'):lineage.append('POINT_IN_TIME_NOT_CONFIRMED')
            if meta.get('future_derived'):lineage.append('FUTURE_DERIVED_BLOCK')
            if str(meta.get('causality_status') or '').upper()!='PASS':lineage.append('CAUSALITY_NOT_CONFIRMED')
        n=int(ar.get('with_n') or 0)
        dr=decay.get(f)
        decay_label=(dr or {}).get('label','INSUFFICIENT')
        red=redundant.get(f) or []
        if protected:
            state='PROTECTED'
            challenger_eligible=True
            reason='Safety/integrity feature is immutable; alpha optimization cannot downweight or disable it.'
        elif 'FUTURE_DERIVED_BLOCK' in lineage or 'POINT_IN_TIME_NOT_CONFIRMED' in lineage:
            state='LEAKAGE_RISK_BLOCK'
            challenger_eligible=False
            reason='Explicit lineage metadata does not clear point-in-time safety.'
        elif meta is None:
            state='UNREGISTERED_RESEARCH_ONLY'
            challenger_eligible=False
            reason='Feature has no inspectable registry metadata.'
        elif n<int(min_forward_n):
            state='FORWARD_EVIDENCE_BUILDING'
            challenger_eligible=False
            reason='Registered feature lacks minimum settled prospective evidence.'
        elif decay_label=='DECAY':
            state='DECAY_REVIEW'
            challenger_eligible=False
            reason='Recent forward association deteriorated versus earlier settled evidence.'
        elif str(lr.get('state')) in {'CHALLENGER_DISABLE','DOWNWEIGHT','QUARANTINE'}:
            state=str(lr.get('state'))
            challenger_eligible=False
            reason=lr.get('reason') or 'Legacy forward governance penalty.'
        else:
            state='CHALLENGER_ELIGIBLE'
            challenger_eligible=True
            reason='Registered PIT-safe feature with sufficient settled forward evidence; still research/challenger only.'
        rows.append({'feature':f,'state':state,'protected':protected,'challenger_eligible':challenger_eligible,
                     'production_eligible':False,'forward_n':n,'attribution_label':ar.get('label'),
                     'legacy_state':lr.get('state'),'decay':dr,'redundancy':red[:5],
                     'registry':meta,'lineage_flags':lineage,'reason':reason})
    summary={}
    for x in rows:summary[x['state']]=summary.get(x['state'],0)+1
    return {'status':'OK','version':'115.0','horizon':horizon,'settled_signals':len(parsed),
            'rows':rows,'redundancy_pairs':redundancy,'decay_rows':list(decay.values()),'summary':summary,
            'policy':'Feature Governance 3.0 is challenger/research-only. New features require explicit provenance, point-in-time safety and settled forward evidence. Redundancy/decay/leakage diagnostics never auto-promote or mutate champion/live scoring.'}
