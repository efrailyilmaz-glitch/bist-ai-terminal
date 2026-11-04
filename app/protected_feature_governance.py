"""V71 protected feature governance and persistent hysteresis.
Safety/integrity features can never be downweighted or disabled by adaptive challenger optimization.
Non-protected penalties/recovery require repeated NEW forward evidence.
"""
from __future__ import annotations
import hashlib,json,sqlite3,time
from pathlib import Path

PROTECTED_PREFIXES=(
    'signal_guard:','trap_defense:','point_in_time:','pit:',
    'execution_guard:','execution:','risk_passport:','data_integrity:',
    'microstructure_guard:','portfolio_guard:','lineage_integrity:'
)
PENALTY_STATES={'QUARANTINE','DOWNWEIGHT','CHALLENGER_DISABLE'}
MULTIPLIERS={'OBSERVE':1.0,'SUPPORTED':1.0,'CONFLICTED':1.0,'QUARANTINE':.85,'DOWNWEIGHT':.65,'CHALLENGER_DISABLE':0.0,'PROTECTED':1.0}

def _db():
    p=Path.home()/'.bist-ai-terminal'/'feature_governance.db'
    p.parent.mkdir(parents=True,exist_ok=True);return p

def _conn():
    c=sqlite3.connect(_db())
    c.execute('''CREATE TABLE IF NOT EXISTS states(
      feature TEXT PRIMARY KEY, applied_state TEXT, raw_state TEXT, last_evidence_hash TEXT,
      bad_streak INTEGER, good_streak INTEGER, updated_epoch REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT, feature TEXT, event TEXT, evidence_hash TEXT,
      created_epoch REAL
    )''')
    c.commit();return c

def is_protected(feature):
    f=str(feature or '')
    return any(f.startswith(p) for p in PROTECTED_PREFIXES)

def _evidence_hash(row):
    payload={'feature':row.get('feature'),'raw_state':row.get('state'),
             'max_with_n':row.get('max_with_n'),'negative_horizons':row.get('negative_horizons'),
             'consistent_horizons':row.get('consistent_horizons'),
             'weighted_delta_mean_excess_pct':row.get('weighted_delta_mean_excess_pct'),
             'evidence':row.get('evidence') or []}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def _read(c,feature):
    r=c.execute('SELECT applied_state,raw_state,last_evidence_hash,bad_streak,good_streak FROM states WHERE feature=?',(str(feature),)).fetchone()
    if not r:return {'applied_state':'OBSERVE','raw_state':'OBSERVE','last_evidence_hash':None,'bad_streak':0,'good_streak':0}
    return {'applied_state':r[0],'raw_state':r[1],'last_evidence_hash':r[2],'bad_streak':int(r[3] or 0),'good_streak':int(r[4] or 0)}

def _event(c,feature,event,evidence_hash):
    c.execute('INSERT INTO events(feature,event,evidence_hash,created_epoch) VALUES(?,?,?,?)',
              (str(feature),str(event),evidence_hash,time.time()))

def apply(rows):
    """Apply protection + persistent hysteresis to V47 raw governance rows."""
    rows=list(rows or []);out=[]
    c=_conn()
    try:
        for raw in rows:
            row=dict(raw);feature=str(row.get('feature') or '');raw_state=str(row.get('state') or 'OBSERVE')
            eh=_evidence_hash(row);s=_read(c,feature);advanced=eh!=s['last_evidence_hash']
            prior=s['applied_state']
            if is_protected(feature):
                applied='PROTECTED';bad=0;good=max(s['good_streak'],0)
                if advanced and prior!='PROTECTED':_event(c,feature,prior+'->PROTECTED',eh)
            else:
                bad=s['bad_streak'];good=s['good_streak'];applied=prior
                if advanced:
                    if raw_state in PENALTY_STATES:
                        bad+=1;good=0
                    else:
                        good+=1;bad=0
                    # Escalation is intentionally slower than the raw V47 label.
                    if raw_state=='CHALLENGER_DISABLE' and bad>=4:applied='CHALLENGER_DISABLE'
                    elif raw_state in {'CHALLENGER_DISABLE','DOWNWEIGHT'} and bad>=3:applied='DOWNWEIGHT'
                    elif raw_state in PENALTY_STATES and bad>=2:applied='QUARANTINE'
                    elif raw_state not in PENALTY_STATES and prior in PENALTY_STATES and good>=3:
                        applied='SUPPORTED' if raw_state=='SUPPORTED' else 'OBSERVE'
                    elif prior not in PENALTY_STATES:
                        applied=raw_state if raw_state in {'SUPPORTED','CONFLICTED','OBSERVE'} else 'OBSERVE'
                    if applied!=prior:_event(c,feature,prior+'->'+applied,eh)
                elif is_protected(feature):
                    applied='PROTECTED'
            c.execute('''INSERT OR REPLACE INTO states(feature,applied_state,raw_state,last_evidence_hash,bad_streak,good_streak,updated_epoch)
                         VALUES(?,?,?,?,?,?,?)''',
                      (feature,applied,raw_state,eh if advanced else s['last_evidence_hash'],bad,good,time.time()))
            row['raw_state']=raw_state;row['state']=applied;row['protected']=is_protected(feature)
            row['challenger_multiplier']=MULTIPLIERS.get(applied,1.0)
            row['hysteresis']={'advanced':advanced,'bad_streak':bad,'good_streak':good,'prior_state':prior}
            if row['protected']:
                row['reason']='Protected safety/integrity feature; adaptive governance cannot downweight or disable it.'
            out.append(row)
        c.commit()
    finally:c.close()
    return out

def status(limit=200):
    c=_conn()
    try:
        states=[{'feature':r[0],'state':r[1],'raw_state':r[2],'bad_streak':r[3],'good_streak':r[4],'updated_epoch':r[5],
                 'protected':is_protected(r[0]),'challenger_multiplier':MULTIPLIERS.get(r[1],1.0)}
                for r in c.execute('SELECT feature,applied_state,raw_state,bad_streak,good_streak,updated_epoch FROM states ORDER BY feature LIMIT ?',
                                   (max(1,min(int(limit),1000)),)).fetchall()]
        events=[{'id':r[0],'feature':r[1],'event':r[2],'evidence_hash':r[3],'created_epoch':r[4]}
                for r in c.execute('SELECT id,feature,event,evidence_hash,created_epoch FROM events ORDER BY id DESC LIMIT ?',
                                   (max(1,min(int(limit),1000)),)).fetchall()]
    finally:c.close()
    return {'status':'OK','protected_prefixes':list(PROTECTED_PREFIXES),'states':states,'events':events,
            'policy':'Protected safety/integrity features are immutable at multiplier 1.0. Non-protected penalties and recovery require repeated new forward evidence.'}
