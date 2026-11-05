"""V70 persistent paper champion recovery and hysteresis governance.
State advances only when a challenger has a NEW rebalance evidence count.
This governs paper-tournament labels only; it never authorizes production/live execution.
"""
from __future__ import annotations
from .runtime_db import connect as db_connect
import sqlite3,time
from pathlib import Path

def _db():
    from .runtime_paths import data_path
    return data_path('champion_governance.db')

def _conn():
    c=db_connect(_db())
    c.execute('''CREATE TABLE IF NOT EXISTS states(
      tournament_id INTEGER, variant_id TEXT, state TEXT, last_rebalance INTEGER,
      bad_streak INTEGER, good_streak INTEGER, updated_epoch REAL,
      PRIMARY KEY(tournament_id,variant_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT, tournament_id INTEGER, variant_id TEXT,
      event TEXT, rebalance_count INTEGER, created_epoch REAL
    )''')
    c.commit();return c

def _state(c,tid,vid):
    r=c.execute('SELECT state,last_rebalance,bad_streak,good_streak FROM states WHERE tournament_id=? AND variant_id=?',
                (int(tid),str(vid))).fetchone()
    return {'state':r[0],'last_rebalance':int(r[1] or 0),'bad_streak':int(r[2] or 0),'good_streak':int(r[3] or 0)} if r else {
        'state':'OBSERVE','last_rebalance':0,'bad_streak':0,'good_streak':0}

def _save(c,tid,vid,s,event=None,evidence=0):
    c.execute('''INSERT OR REPLACE INTO states(tournament_id,variant_id,state,last_rebalance,bad_streak,good_streak,updated_epoch)
      VALUES(?,?,?,?,?,?,?)''',(int(tid),str(vid),s['state'],int(s['last_rebalance']),int(s['bad_streak']),int(s['good_streak']),time.time()))
    if event:
        c.execute('INSERT INTO events(tournament_id,variant_id,event,rebalance_count,created_epoch) VALUES(?,?,?,?,?)',
                  (int(tid),str(vid),event,int(evidence),time.time()))

def evaluate(tournament_id,rows,current_champion=None,challenger_margin=2.5,quarantine_streak=2,recovery_streak=3):
    rows=list(rows or [])
    c=_conn()
    try:
        states={}
        for row in rows:
            vid=str(row.get('id'));m=row.get('metrics') or {};evidence=int(m.get('rebalance_count') or 0)
            decay=(row.get('decay_v2') or {}).get('status')
            eligible=m.get('status')=='ELIGIBLE'
            s=_state(c,tournament_id,vid);prior=s['state'];advanced=evidence>s['last_rebalance']
            if advanced:
                s['last_rebalance']=evidence
                if decay=='DECAY':
                    s['bad_streak']+=1;s['good_streak']=0
                elif eligible and decay=='STABLE':
                    s['good_streak']+=1;s['bad_streak']=0
                else:
                    s['good_streak']=0
                    if decay!='DECAY':s['bad_streak']=0
            is_champion=vid==current_champion
            if is_champion:
                if s['bad_streak']>=quarantine_streak:s['state']='QUARANTINE'
                elif prior=='QUARANTINE' and s['good_streak']>=recovery_streak:s['state']='ACTIVE'
                elif decay=='WATCH':s['state']='WATCH'
                elif decay=='STABLE' and eligible:s['state']='ACTIVE'
                elif prior not in {'QUARANTINE'}:s['state']='WATCH'
            else:
                s['state']='CHALLENGER_READY' if eligible and decay!='DECAY' and s['good_streak']>=recovery_streak else 'OBSERVE'
            evt=None
            if advanced and s['state']!=prior:evt=prior+'->'+s['state']
            _save(c,tournament_id,vid,s,evt,evidence);states[vid]={**s,'advanced':advanced}
        c.commit()
        ev=[{'id':r[0],'variant_id':r[1],'event':r[2],'rebalance_count':r[3],'created_epoch':r[4]}
            for r in c.execute('SELECT id,variant_id,event,rebalance_count,created_epoch FROM events WHERE tournament_id=? ORDER BY id DESC LIMIT 50',(int(tournament_id),)).fetchall()]
    finally:
        c.close()
    by={str(r.get('id')):r for r in rows}
    ready=[r for r in rows if states.get(str(r.get('id')),{}).get('state')=='CHALLENGER_READY']
    ready.sort(key=lambda r:-(float((r.get('metrics') or {}).get('score') or -1e18)))
    decision={'action':'HOLD','paper_champion':current_champion,'reason':'HYSTERESIS'}
    if not current_champion:
        if ready:
            decision={'action':'NOMINATE_PAPER_CHAMPION','paper_champion':ready[0]['id'],'reason':'THREE_NEW_HEALTHY_EVIDENCE_POINTS'}
        else:
            decision={'action':'HOLD','paper_champion':None,'reason':'NO_MATURE_CHALLENGER'}
    else:
        cs=states.get(str(current_champion),{})
        incumbent=by.get(str(current_champion),{})
        incumbent_score=float((incumbent.get('metrics') or {}).get('score') or -1e18)
        if cs.get('state')=='QUARANTINE':
            if ready:
                best=ready[0];best_score=float((best.get('metrics') or {}).get('score') or -1e18)
                if best_score>=incumbent_score+challenger_margin:
                    decision={'action':'ROTATE_PAPER_CHAMPION','paper_champion':best['id'],'reason':'QUARANTINED_INCUMBENT_AND_CHALLENGER_MARGIN'}
                else:
                    decision={'action':'QUARANTINE_HOLD','paper_champion':current_champion,'reason':'NO_CHALLENGER_MARGIN'}
            else:
                decision={'action':'QUARANTINE_HOLD','paper_champion':current_champion,'reason':'NO_MATURE_CHALLENGER'}
        else:
            candidates=[r for r in ready if str(r.get('id'))!=str(current_champion)]
            if candidates:
                best=candidates[0];best_score=float((best.get('metrics') or {}).get('score') or -1e18)
                if best_score>=incumbent_score+challenger_margin:
                    decision={'action':'ROTATE_PAPER_CHAMPION','paper_champion':best['id'],'reason':'CHALLENGER_MARGIN_AND_PERSISTENCE'}
    return {'status':'OK','current_champion':current_champion,'decision':decision,'states':states,'events':ev,
            'policy':'Paper-tournament champion label only. No live execution or production promotion is authorized.'}

def status(tournament_id):
    c=_conn()
    try:
        rows=c.execute('SELECT variant_id,state,last_rebalance,bad_streak,good_streak,updated_epoch FROM states WHERE tournament_id=?',(int(tournament_id),)).fetchall()
        ev=c.execute('SELECT id,variant_id,event,rebalance_count,created_epoch FROM events WHERE tournament_id=? ORDER BY id DESC LIMIT 50',(int(tournament_id),)).fetchall()
    finally:
        c.close()
    return {'status':'OK','states':[{'variant_id':r[0],'state':r[1],'last_rebalance':r[2],'bad_streak':r[3],'good_streak':r[4],'updated_epoch':r[5]} for r in rows],
            'events':[{'id':r[0],'variant_id':r[1],'event':r[2],'rebalance_count':r[3],'created_epoch':r[4]} for r in ev]}
