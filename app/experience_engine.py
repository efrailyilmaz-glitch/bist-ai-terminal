from __future__ import annotations
import json, os, platform, sqlite3, threading, time, hashlib
from datetime import datetime, timezone
from pathlib import Path
from .runtime_db import connect as db_connect
from .market_data import yahoo_rows
from .point_in_time import audit_signal

_LOCK=threading.Lock()

def _dir():
    from .runtime_paths import data_root
    return data_root()
def _db():return _dir()/'experience.db'
def _conn():
    c=db_connect(_db(),timeout=15)
    c.execute('''CREATE TABLE IF NOT EXISTS signals(
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_epoch REAL, created_at TEXT, ticker TEXT, grade TEXT,
      opportunity_score REAL, committee_decision TEXT, committee_score REAL, regime TEXT, entry_price REAL,
      benchmark_price REAL, setup_json TEXT, settled_5 INTEGER DEFAULT 0, settled_20 INTEGER DEFAULT 0, settled_60 INTEGER DEFAULT 0,
      ret_5 REAL, excess_5 REAL, ret_20 REAL, excess_20 REAL, ret_60 REAL, excess_60 REAL
    )''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_signals_ticker_time ON signals(ticker,created_epoch)')
    cols={r[1] for r in c.execute('PRAGMA table_info(signals)').fetchall()}
    for name,typ in [('source_as_of','TEXT'),('observed_at','TEXT'),('payload_hash','TEXT'),('prev_hash','TEXT'),('ledger_hash','TEXT'),('pit_status','TEXT'),('pit_flags_json','TEXT')]:
        if name not in cols:c.execute(f'ALTER TABLE signals ADD COLUMN {name} {typ}')
    c.execute('''CREATE TABLE IF NOT EXISTS settlements(
      id INTEGER PRIMARY KEY AUTOINCREMENT, signal_id INTEGER, horizon INTEGER, settled_epoch REAL, ret REAL, excess REAL,
      payload_hash TEXT, UNIQUE(signal_id,horizon)
    )''')
    c.commit();return c

def _latest_price(ticker):
    rows=(yahoo_rows(ticker,period='1mo',interval='1d').get('candles') or [])
    return float(rows[-1]['close']) if rows else None

def _canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str)

def _num(x):
    try:return None if x is None else float(x)
    except Exception:return None

def _immutable(created_epoch,ticker,grade,opportunity_score,committee_decision,committee_score,regime,entry_price,benchmark_price,source_as_of,setup,pit_status,pit_flags):
    return {'created_epoch':round(float(created_epoch),6),'ticker':str(ticker),'grade':grade,'opportunity_score':_num(opportunity_score),
            'committee_decision':committee_decision,'committee_score':_num(committee_score),'regime':regime,
            'entry_price':_num(entry_price),'benchmark_price':_num(benchmark_price),'source_as_of':source_as_of,
            'setup':setup,'pit_status':pit_status,'pit_flags':list(pit_flags or [])}

def record_signal(signal,committee=None):
    ticker=(signal or {}).get('ticker')
    if not ticker:return None
    now=time.time();committee=committee or {};pit=audit_signal(signal,now)
    if pit['status']=='BLOCK':return None
    with _LOCK:
        c=_conn()
        prev=c.execute('SELECT id,created_epoch FROM signals WHERE ticker=? ORDER BY created_epoch DESC LIMIT 1',(ticker,)).fetchone()
        if prev and now-float(prev[1])<6*3600:
            c.close();return prev[0]
        entry=float((signal or {}).get('price') or _latest_price(ticker) or 0)
        bench=float(_latest_price('XU100') or 0)
        setup={'confirmations':signal.get('confirmations'),'warnings':signal.get('warnings'),'components':signal.get('components'),
               'targets':signal.get('targets'),'committee_evidence':committee.get('evidence'),'vetoes':committee.get('vetoes'),'committee_gates':committee.get('gates'),
               'signal_guard':signal.get('signal_guard'),'trap_defense':signal.get('trap_defense'),
               'governance_challenger_score':signal.get('governance_challenger_score'),'governance_score_delta':signal.get('governance_score_delta'),'governance_details':signal.get('governance_details')}
        immutable=_immutable(now,ticker,signal.get('grade'),signal.get('opportunity_score'),committee.get('decision'),committee.get('committee_score'),committee.get('regime'),entry,bench,signal.get('as_of'),setup,pit['status'],pit['flags'])
        payload_hash=hashlib.sha256(_canon(immutable).encode()).hexdigest()
        last=c.execute('SELECT ledger_hash FROM signals WHERE ledger_hash IS NOT NULL ORDER BY id DESC LIMIT 1').fetchone()
        prev_hash=(last[0] if last and last[0] else 'GENESIS')
        ledger_hash=hashlib.sha256((prev_hash+'|'+payload_hash).encode()).hexdigest()
        cur=c.execute('''INSERT INTO signals(created_epoch,created_at,ticker,grade,opportunity_score,committee_decision,committee_score,regime,entry_price,benchmark_price,setup_json,
                         source_as_of,observed_at,payload_hash,prev_hash,ledger_hash,pit_status,pit_flags_json)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
          (now,time.strftime('%d.%m.%Y %H:%M:%S'),ticker,signal.get('grade'),signal.get('opportunity_score'),committee.get('decision'),
           committee.get('committee_score'),committee.get('regime'),entry,bench,_canon(setup),signal.get('as_of'),pit['observed_at'],
           payload_hash,prev_hash,ledger_hash,pit['status'],_canon(pit['flags'])))
        c.commit();rid=cur.lastrowid;c.close();return rid

def _future_return(ticker,created_epoch,horizon):
    rows=(yahoo_rows(ticker,period='1y',interval='1d').get('candles') or [])
    if not rows:return None
    dt=datetime.fromtimestamp(created_epoch,tz=timezone.utc).date()
    idx=None
    for i,r in enumerate(rows):
        try:
            rd=datetime.fromisoformat(str(r['time']).replace('Z','+00:00')).date()
        except Exception:
            try:rd=datetime.strptime(str(r['time'])[:10],'%Y-%m-%d').date()
            except Exception:continue
        if rd>=dt:idx=i;break
    if idx is None or idx+horizon>=len(rows):return None
    p0=float(rows[idx]['close']);p1=float(rows[idx+horizon]['close'])
    return (p1/p0-1)*100 if p0 else None

def settle_due(limit=200):
    with _LOCK:
        c=_conn();rows=c.execute('SELECT id,created_epoch,ticker,settled_5,settled_20,settled_60 FROM signals ORDER BY created_epoch ASC LIMIT ?', (int(limit),)).fetchall()
        changed=0
        for rid,epoch,ticker,s5,s20,s60 in rows:
            for h,flag in [(5,s5),(20,s20),(60,s60)]:
                if flag:continue
                r=_future_return(ticker,epoch,h);b=_future_return('XU100',epoch,h)
                if r is None or b is None:continue
                rr,xx=round(r,3),round(r-b,3)
                ph=hashlib.sha256(_canon({'signal_id':rid,'horizon':h,'ret':rr,'excess':xx}).encode()).hexdigest()
                c.execute('INSERT OR IGNORE INTO settlements(signal_id,horizon,settled_epoch,ret,excess,payload_hash) VALUES(?,?,?,?,?,?)',(rid,h,time.time(),rr,xx,ph))
                c.execute(f'UPDATE signals SET settled_{h}=1, ret_{h}=?, excess_{h}=? WHERE id=?',(rr,xx,rid));changed+=1
        c.commit();c.close();return {'updated':changed}

def history(limit=200):
    with _LOCK:
        c=_conn();c.row_factory=sqlite3.Row
        rows=[dict(x) for x in c.execute('SELECT * FROM signals ORDER BY created_epoch DESC LIMIT ?', (max(1,min(int(limit),1000)),)).fetchall()]
        c.close()
    for r in rows:r.pop('setup_json',None)
    return {'rows':rows}

def calibration():
    with _LOCK:
        c=_conn();c.row_factory=sqlite3.Row;rows=[dict(x) for x in c.execute('SELECT * FROM signals').fetchall()];c.close()
    def summ(h,flt=lambda x:True):
        vals=[r.get(f'excess_{h}') for r in rows if flt(r) and r.get(f'settled_{h}') and r.get(f'excess_{h}') is not None]
        if not vals:return {'n':0}
        vals=[float(x) for x in vals]
        return {'n':len(vals),'hit_rate_pct':round(sum(1 for x in vals if x>0)/len(vals)*100,1),
                'mean_excess_pct':round(sum(vals)/len(vals),2),'median_excess_pct':round(sorted(vals)[len(vals)//2],2)}
    by_grade={g:{'5d':summ(5,lambda r,g=g:r.get('grade')==g),'20d':summ(20,lambda r,g=g:r.get('grade')==g),'60d':summ(60,lambda r,g=g:r.get('grade')==g)} for g in ['MEGA','STRONG','WATCH']}
    by_committee={g:{'20d':summ(20,lambda r,g=g:r.get('committee_decision')==g),'60d':summ(60,lambda r,g=g:r.get('committee_decision')==g)} for g in ['PASS','WATCH','NO_TRADE']}
    return {'total_signals':len(rows),'overall':{'5d':summ(5),'20d':summ(20),'60d':summ(60)},'by_grade':by_grade,'by_committee':by_committee,
            'note':'Prospective live ledger: only signals recorded at the time they occurred are used. This avoids historical look-ahead in the live experience score.'}


def verify_ledger():
    """Verify append-only hash chain for V43+ evidence rows."""
    with _LOCK:
        c=_conn();c.row_factory=sqlite3.Row
        rows=[dict(x) for x in c.execute('SELECT * FROM signals WHERE ledger_hash IS NOT NULL ORDER BY id').fetchall()];c.close()
    prev='GENESIS';bad=[]
    for r in rows:
        try:
            setup=json.loads(r.get('setup_json') or '{}');flags=json.loads(r.get('pit_flags_json') or '[]')
            immutable=_immutable(r['created_epoch'],r['ticker'],r.get('grade'),r.get('opportunity_score'),r.get('committee_decision'),r.get('committee_score'),r.get('regime'),r.get('entry_price'),r.get('benchmark_price'),r.get('source_as_of'),setup,r.get('pit_status'),flags)
            ph=hashlib.sha256(_canon(immutable).encode()).hexdigest();lh=hashlib.sha256((prev+'|'+ph).encode()).hexdigest()
            if ph!=r.get('payload_hash') or r.get('prev_hash')!=prev or lh!=r.get('ledger_hash'):bad.append(r['id'])
            prev=r.get('ledger_hash') or prev
        except Exception:bad.append(r.get('id'))
    return {'status':'PASS' if not bad else 'FAIL','rows':len(rows),'bad_ids':bad[:20],
            'note':'V43+ signal evidence is hash-chained; legacy pre-V43 rows are outside this chain.'}
