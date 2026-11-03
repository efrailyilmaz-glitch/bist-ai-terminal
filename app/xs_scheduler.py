"""V56 autonomous paper-only scheduler for XS tournaments.
Marks active challenger portfolios daily and rebalances only from the prospective
current XS ranking. Missing optional model dependencies cause WAIT, never fallback.
"""
from __future__ import annotations
import threading,time
from datetime import date,datetime
from . import xs_tournament
from .cross_sectional_ml import current_ranking
from .xs_portfolio import construct

_LOCK=threading.RLock()
_THREAD=None
_STOP=False

def _ensure_columns(c):
    cols={r[1] for r in c.execute('PRAGMA table_info(tournaments)').fetchall()}
    wanted=[
      ('scheduler_enabled','INTEGER DEFAULT 0'),('last_mark_day','TEXT'),('last_rebalance_day','TEXT'),
      ('rebalance_every_days','INTEGER DEFAULT 5'),('scheduler_cost_bps','REAL DEFAULT 20'),
      ('scheduler_max_names','INTEGER DEFAULT 10'),('scheduler_max_weight','REAL DEFAULT .15'),
      ('scheduler_adv_limit_pct','REAL DEFAULT 1.0'),('scheduler_limit','INTEGER DEFAULT 120')
    ]
    for name,typ in wanted:
        if name not in cols:c.execute(f'ALTER TABLE tournaments ADD COLUMN {name} {typ}')
    c.commit()

def configure(tournament_id,enabled=None,rebalance_every_days=None,cost_bps=None,max_names=None,max_weight=None,adv_limit_pct=None,limit=None):
    with _LOCK:
        c=xs_tournament._conn();_ensure_columns(c)
        row=c.execute('SELECT id FROM tournaments WHERE id=?',(int(tournament_id),)).fetchone()
        if not row:c.close();return {'status':'NOT_FOUND'}
        fields=[];vals=[]
        for k,v in [
          ('scheduler_enabled',None if enabled is None else int(bool(enabled))),
          ('rebalance_every_days',None if rebalance_every_days is None else max(1,min(int(rebalance_every_days),20))),
          ('scheduler_cost_bps',None if cost_bps is None else max(0,min(float(cost_bps),200))),
          ('scheduler_max_names',None if max_names is None else max(3,min(int(max_names),20))),
          ('scheduler_max_weight',None if max_weight is None else max(.05,min(float(max_weight),.50))),
          ('scheduler_adv_limit_pct',None if adv_limit_pct is None else max(.1,min(float(adv_limit_pct),10))),
          ('scheduler_limit',None if limit is None else max(20,min(int(limit),500)))
        ]:
            if v is not None:fields.append(k+'=?');vals.append(v)
        if fields:
            vals.append(int(tournament_id))
            c.execute('UPDATE tournaments SET '+','.join(fields)+' WHERE id=?',tuple(vals));c.commit()
        out=_state_conn(c,int(tournament_id));c.close()
    return out

def _state_conn(c,tournament_id):
    _ensure_columns(c)
    c.row_factory=None
    cols=[x[1] for x in c.execute('PRAGMA table_info(tournaments)').fetchall()]
    row=c.execute('SELECT * FROM tournaments WHERE id=?',(int(tournament_id),)).fetchone()
    if not row:return {'status':'NOT_FOUND'}
    d=dict(zip(cols,row))
    return {'status':'OK','tournament_id':tournament_id,'enabled':bool(d.get('scheduler_enabled')),
            'last_mark_day':d.get('last_mark_day'),'last_rebalance_day':d.get('last_rebalance_day'),
            'rebalance_every_days':int(d.get('rebalance_every_days') or 5),
            'cost_bps':float(d.get('scheduler_cost_bps') or 20),
            'max_names':int(d.get('scheduler_max_names') or 10),
            'max_weight':float(d.get('scheduler_max_weight') or .15),
            'adv_limit_pct':float(d.get('scheduler_adv_limit_pct') or 1.0),
            'limit':int(d.get('scheduler_limit') or 120),'started_at':d.get('started_at')}

def state(tournament_id):
    with _LOCK:
        c=xs_tournament._conn();out=_state_conn(c,int(tournament_id));c.close();return out

def _business_days_since(day_text,today_text):
    if not day_text:return 999
    try:
        a=datetime.fromisoformat(day_text).date();b=datetime.fromisoformat(today_text).date()
    except Exception:return 999
    if b<=a:return 0
    n=0;d=a
    from datetime import timedelta
    while d<b:
        d+=timedelta(days=1)
        if d.weekday()<5:n+=1
    return n

def run_once(tournament_id,today=None,force_rebalance=False):
    day=str(today or date.today())
    st=state(tournament_id)
    if st.get('status')!='OK':return st
    if not st.get('enabled') or not st.get('started_at'):
        return {'status':'PAUSED','scheduler':st}
    marks=None
    if st.get('last_mark_day')!=day:
        marks=xs_tournament.mark_all(tournament_id)
        with _LOCK:
            c=xs_tournament._conn();_ensure_columns(c)
            c.execute('UPDATE tournaments SET last_mark_day=? WHERE id=?',(day,int(tournament_id)));c.commit();c.close()
    due=force_rebalance or _business_days_since(st.get('last_rebalance_day'),day)>=st.get('rebalance_every_days',5)
    if not due:
        return {'status':'MARKED' if marks else 'IDLE','mark':marks,'scheduler':state(tournament_id)}
    ranking=current_ranking(limit=st.get('limit',120))
    if ranking.get('status')!='OK':
        return {'status':'WAIT_MODEL','ranking_status':ranking.get('status'),'mark':marks,
                'scheduler':state(tournament_id),'note':'No fallback ranking is used.'}
    snap=xs_tournament.snapshot(tournament_id)
    results=[]
    for ch in snap.get('challengers') or []:
        method=ch.get('method') or 'score_inverse_vol'
        paper=ch.get('paper') or {};port=paper.get('portfolio') or {}
        pv=float(port.get('last_equity') or snap.get('capital_each') or 1_000_000)
        built=construct(ranking.get('rows') or [],portfolio_value=pv,max_names=st['max_names'],
                        max_weight=st['max_weight'],adv_limit_pct=st['adv_limit_pct'],method=method)
        if built.get('status')!='OK':
            results.append({'variant_id':ch.get('id'),'status':'CONSTRUCT_WAIT','detail':built.get('status')});continue
        rb=xs_tournament.rebalance_variant(tournament_id,ch.get('id'),built.get('rows') or [],st['cost_bps'])
        results.append({'variant_id':ch.get('id'),'status':rb.get('status'),'rebalance':rb,
                        'portfolio_stats':{k:built.get(k) for k in ['annual_volatility_pct','avg_correlation','liquidity_flags']}})
    if any(x.get('status')=='OK' for x in results):
        with _LOCK:
            c=xs_tournament._conn();_ensure_columns(c)
            c.execute('UPDATE tournaments SET last_rebalance_day=? WHERE id=?',(day,int(tournament_id)));c.commit();c.close()
    return {'status':'REBALANCED' if any(x.get('status')=='OK' for x in results) else 'WAIT_PORTFOLIO',
            'as_of':ranking.get('as_of'),'ranked_symbols':ranking.get('symbols'),'mark':marks,'results':results,
            'scheduler':state(tournament_id)}

def run_all_once():
    with _LOCK:
        c=xs_tournament._conn();_ensure_columns(c)
        ids=[r[0] for r in c.execute('SELECT id FROM tournaments WHERE scheduler_enabled=1 AND started_epoch IS NOT NULL').fetchall()];c.close()
    out=[]
    for tid in ids:
        try:out.append({'tournament_id':tid,**run_once(tid)})
        except Exception as e:out.append({'tournament_id':tid,'status':'ERROR','error':str(e)[:160]})
    return {'status':'OK','rows':out}

def _loop():
    global _STOP
    while not _STOP:
        try:run_all_once()
        except Exception:pass
        time.sleep(60)

def start_worker():
    global _THREAD,_STOP
    with _LOCK:
        _STOP=False
        if not (_THREAD and _THREAD.is_alive()):
            _THREAD=threading.Thread(target=_loop,daemon=True,name='XSPaperScheduler');_THREAD.start()
    return {'status':'OK','running':True}
