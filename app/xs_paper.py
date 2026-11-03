"""V54 persistent paper ledger for cross-sectional challenger portfolios.
Prospective only. No broker calls and no live order path.
"""
from __future__ import annotations
import json, math, sqlite3, threading, time
from pathlib import Path
from .market_data import yahoo_rows

_LOCK=threading.RLock()

def _db():
    p=Path.home()/'.bist-ai-terminal'/'xs_paper.db'
    p.parent.mkdir(parents=True,exist_ok=True)
    return p

def _conn():
    c=sqlite3.connect(_db())
    c.execute('''CREATE TABLE IF NOT EXISTS portfolios(
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_epoch REAL, created_at TEXT, name TEXT,
      capital REAL, benchmark TEXT, status TEXT, last_equity REAL, peak_equity REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS rebalances(
      id INTEGER PRIMARY KEY AUTOINCREMENT, portfolio_id INTEGER, epoch REAL, at TEXT,
      target_json TEXT, turnover_pct REAL, cost REAL, equity_before REAL, equity_after REAL,
      model_registry_id INTEGER, model_fingerprint TEXT, ranking_as_of TEXT, ranking_snapshot_json TEXT
    )''')
    cols={r[1] for r in c.execute('PRAGMA table_info(rebalances)').fetchall()}
    for name,typ in [('model_registry_id','INTEGER'),('model_fingerprint','TEXT'),('ranking_as_of','TEXT'),('ranking_snapshot_json','TEXT')]:
        if name not in cols:c.execute(f'ALTER TABLE rebalances ADD COLUMN {name} {typ}')
    c.execute('''CREATE TABLE IF NOT EXISTS positions(
      portfolio_id INTEGER, ticker TEXT, weight REAL, units REAL, entry_price REAL,
      PRIMARY KEY(portfolio_id,ticker)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS curve(
      id INTEGER PRIMARY KEY AUTOINCREMENT, portfolio_id INTEGER, epoch REAL, at TEXT,
      equity REAL, benchmark_equity REAL, drawdown_pct REAL, excess_pct REAL
    )''')
    c.commit();return c

def _price(ticker):
    try:
        rows=(yahoo_rows(ticker,period='1mo',interval='1d').get('candles') or [])
        return float(rows[-1]['close']) if rows else None
    except Exception:return None

def create(name='XS Challenger',capital=1_000_000,benchmark='XU100'):
    now=time.time()
    with _LOCK:
        c=_conn();cur=c.execute('INSERT INTO portfolios(created_epoch,created_at,name,capital,benchmark,status,last_equity,peak_equity) VALUES(?,?,?,?,?,?,?,?)',
            (now,time.strftime('%d.%m.%Y %H:%M:%S'),name,float(capital),benchmark,'ACTIVE',float(capital),float(capital)))
        c.commit();pid=cur.lastrowid;c.close()
    return {'status':'OK','portfolio_id':pid}

def rebalance(portfolio_id,target_rows,one_way_cost_bps=20,lineage=None):
    with _LOCK:
        c=_conn();p=c.execute('SELECT capital,last_equity,benchmark FROM portfolios WHERE id=?',(int(portfolio_id),)).fetchone()
        if not p:c.close();return {'status':'NOT_FOUND'}
        equity=float(p[1]);current={r[0]:r for r in c.execute('SELECT ticker,weight,units,entry_price FROM positions WHERE portfolio_id=?',(int(portfolio_id),)).fetchall()}
        tgt={str(x['ticker']).upper().replace('.IS',''):float(x['weight_pct'])/100 for x in (target_rows or []) if x.get('ticker') and float(x.get('weight_pct') or 0)>0}
        s=sum(tgt.values())
        if s<=0:c.close();return {'status':'NO_TARGETS'}
        tgt={k:v/s for k,v in tgt.items()}
        alln=set(current)|set(tgt);turn=.5*sum(abs(tgt.get(k,0)-float(current.get(k,[None,0])[1] or 0)) for k in alln)
        cost=equity*turn*float(one_way_cost_bps)/10000
        equity_after=max(0,equity-cost)
        c.execute('DELETE FROM positions WHERE portfolio_id=?',(int(portfolio_id),))
        applied=[]
        for code,w in tgt.items():
            px=_price(code)
            if not px or px<=0:continue
            alloc=equity_after*w;units=alloc/px
            c.execute('INSERT OR REPLACE INTO positions(portfolio_id,ticker,weight,units,entry_price) VALUES(?,?,?,?,?)',(int(portfolio_id),code,w,units,px))
            applied.append({'ticker':code,'weight_pct':round(w*100,3),'units':round(units,6),'entry_price':round(px,4)})
        now=time.time()
        lineage=lineage or {};artifact=lineage.get('model_artifact') or {}
        c.execute('''INSERT INTO rebalances(portfolio_id,epoch,at,target_json,turnover_pct,cost,equity_before,equity_after,
                  model_registry_id,model_fingerprint,ranking_as_of,ranking_snapshot_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (int(portfolio_id),now,time.strftime('%d.%m.%Y %H:%M:%S'),json.dumps(applied,ensure_ascii=False),turn*100,cost,equity,equity_after,
                   artifact.get('registry_id'),artifact.get('model_fingerprint'),lineage.get('ranking_as_of'),json.dumps(lineage.get('ranking_snapshot') or [],ensure_ascii=False)))
        c.execute('UPDATE portfolios SET last_equity=? WHERE id=?',(equity_after,int(portfolio_id)));c.commit();c.close()
    return {'status':'OK','portfolio_id':portfolio_id,'turnover_pct':round(turn*100,2),'cost':round(cost,2),'equity_after_cost':round(equity_after,2),'positions':applied,
            'model_registry_id':(lineage or {}).get('model_artifact',{}).get('registry_id') if lineage else None}

def mark(portfolio_id):
    with _LOCK:
        c=_conn();p=c.execute('SELECT capital,last_equity,peak_equity,benchmark,created_epoch FROM portfolios WHERE id=?',(int(portfolio_id),)).fetchone()
        if not p:c.close();return {'status':'NOT_FOUND'}
        capital,last,peak,benchmark,created=p
        positions=c.execute('SELECT ticker,weight,units,entry_price FROM positions WHERE portfolio_id=?',(int(portfolio_id),)).fetchall()
        equity=0.0;missing=[]
        for code,w,units,entry in positions:
            px=_price(code)
            if not px:missing.append(code);px=float(entry)
            equity+=float(units)*px
        if not positions:equity=float(last)
        peak=max(float(peak),equity);dd=(equity/peak-1)*100 if peak else 0
        bench_now=_price(benchmark)
        bench_start=None
        try:
            rows=(yahoo_rows(benchmark,period='1y',interval='1d').get('candles') or [])
            if rows:bench_start=float(rows[0]['close'])
        except Exception:pass
        benchmark_equity=float(capital)*(bench_now/bench_start) if bench_now and bench_start else float(capital)
        excess=((equity/float(capital)-1)-(benchmark_equity/float(capital)-1))*100
        now=time.time()
        c.execute('INSERT INTO curve(portfolio_id,epoch,at,equity,benchmark_equity,drawdown_pct,excess_pct) VALUES(?,?,?,?,?,?,?)',
                  (int(portfolio_id),now,time.strftime('%d.%m.%Y %H:%M:%S'),equity,benchmark_equity,dd,excess))
        c.execute('UPDATE portfolios SET last_equity=?,peak_equity=? WHERE id=?',(equity,peak,int(portfolio_id)));c.commit();c.close()
    return {'status':'OK','portfolio_id':portfolio_id,'equity':round(equity,2),'benchmark_equity':round(benchmark_equity,2),
            'drawdown_pct':round(dd,2),'excess_pct':round(excess,2),'missing_prices':missing}

def history(portfolio_id,limit=200):
    with _LOCK:
        c=_conn();c.row_factory=sqlite3.Row
        p=c.execute('SELECT * FROM portfolios WHERE id=?',(int(portfolio_id),)).fetchone()
        if not p:c.close();return {'status':'NOT_FOUND'}
        curve=[dict(x) for x in c.execute('SELECT * FROM curve WHERE portfolio_id=? ORDER BY id DESC LIMIT ?',(int(portfolio_id),max(1,min(int(limit),1000)))).fetchall()]
        rebs=[dict(x) for x in c.execute('SELECT * FROM rebalances WHERE portfolio_id=? ORDER BY id DESC LIMIT 100',(int(portfolio_id),)).fetchall()]
        pos=[dict(x) for x in c.execute('SELECT * FROM positions WHERE portfolio_id=? ORDER BY weight DESC',(int(portfolio_id),)).fetchall()];c.close()
    return {'status':'OK','portfolio':dict(p),'curve':curve,'rebalances':rebs,'positions':pos}
