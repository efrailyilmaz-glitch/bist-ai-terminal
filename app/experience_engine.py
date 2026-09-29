from __future__ import annotations
import json, os, platform, sqlite3, threading, time
from datetime import datetime, timezone
from pathlib import Path
from .market_data import yahoo_rows

_LOCK=threading.Lock()

def _dir():
    if platform.system()=='Darwin':b=Path.home()/'Library'/'Application Support'/'BIST AI Terminal'
    elif platform.system()=='Windows':b=Path(os.getenv('APPDATA') or Path.home())/'BIST AI Terminal'
    else:b=Path.home()/'.bist-ai-terminal'
    b.mkdir(parents=True,exist_ok=True);return b
def _db():return _dir()/'experience.db'
def _conn():
    c=sqlite3.connect(_db(),timeout=15)
    c.execute('''CREATE TABLE IF NOT EXISTS signals(
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_epoch REAL, created_at TEXT, ticker TEXT, grade TEXT,
      opportunity_score REAL, committee_decision TEXT, committee_score REAL, regime TEXT, entry_price REAL,
      benchmark_price REAL, setup_json TEXT, settled_5 INTEGER DEFAULT 0, settled_20 INTEGER DEFAULT 0, settled_60 INTEGER DEFAULT 0,
      ret_5 REAL, excess_5 REAL, ret_20 REAL, excess_20 REAL, ret_60 REAL, excess_60 REAL
    )''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_signals_ticker_time ON signals(ticker,created_epoch)')
    c.commit();return c

def _latest_price(ticker):
    rows=(yahoo_rows(ticker,period='1mo',interval='1d').get('candles') or [])
    return float(rows[-1]['close']) if rows else None

def record_signal(signal,committee=None):
    ticker=(signal or {}).get('ticker')
    if not ticker:return None
    now=time.time();committee=committee or {}
    with _LOCK:
        c=_conn()
        prev=c.execute('SELECT id,created_epoch FROM signals WHERE ticker=? ORDER BY created_epoch DESC LIMIT 1',(ticker,)).fetchone()
        if prev and now-float(prev[1])<6*3600:
            c.close();return prev[0]
        entry=float((signal or {}).get('price') or _latest_price(ticker) or 0)
        bench=float(_latest_price('XU100') or 0)
        setup={'confirmations':signal.get('confirmations'),'warnings':signal.get('warnings'),'components':signal.get('components'),
               'targets':signal.get('targets'),'committee_evidence':committee.get('evidence'),'vetoes':committee.get('vetoes')}
        cur=c.execute('''INSERT INTO signals(created_epoch,created_at,ticker,grade,opportunity_score,committee_decision,committee_score,regime,entry_price,benchmark_price,setup_json)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
          (now,time.strftime('%d.%m.%Y %H:%M:%S'),ticker,signal.get('grade'),signal.get('opportunity_score'),committee.get('decision'),
           committee.get('committee_score'),committee.get('regime'),entry,bench,json.dumps(setup,ensure_ascii=False)))
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
                c.execute(f'UPDATE signals SET settled_{h}=1, ret_{h}=?, excess_{h}=? WHERE id=?',(round(r,3),round(r-b,3),rid));changed+=1
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
