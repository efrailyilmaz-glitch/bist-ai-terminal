"""V79 autonomous research loop.
Orchestrates research validation -> implementation reality -> prospective paper tournament
-> forward governance. Paper/research only; no broker path and no live promotion.
"""
from __future__ import annotations
from contextlib import closing
import hashlib,json,sqlite3,time
from .runtime_db import connect as db_connect
from .runtime_paths import data_path
from .cross_sectional_ml import purged_walk_forward_cost_reality
from . import xs_tournament, xs_scheduler
from .pit_universe import dataset_status as pit_universe_status

def _db():return data_path('research_loop.db')

def _conn():
    c=db_connect(_db())
    c.execute('''CREATE TABLE IF NOT EXISTS experiments(
      config_hash TEXT PRIMARY KEY, created_epoch REAL, tournament_id INTEGER, status TEXT, config_json TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS runs(
      id INTEGER PRIMARY KEY AUTOINCREMENT, config_hash TEXT, created_epoch REAL, status TEXT, result_json TEXT
    )''')
    c.commit();return c

def _hash(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def _existing(config_hash):
    with closing(_conn()) as c, c:
        r=c.execute('SELECT tournament_id,status FROM experiments WHERE config_hash=?',(config_hash,)).fetchone()
    return {'tournament_id':r[0],'status':r[1]} if r else None

def _save_run(config_hash,status,result):
    now=time.time()
    with closing(_conn()) as c, c:
        c.execute('INSERT INTO runs(config_hash,created_epoch,status,result_json) VALUES(?,?,?,?)',
                  (config_hash,now,status,json.dumps(result,ensure_ascii=False,sort_keys=True,default=str)))
        c.execute('UPDATE experiments SET status=? WHERE config_hash=?',(status,config_hash))
    return now

def run_once(tickers=None,period='5y',limit=120,train_days=252,test_days=63,purge_days=5,embargo_days=5,
             one_way_cost_bps=20,rebalance_every=5,portfolio_value=1_000_000,adv_limit_pct=1.0,
             auto_create_paper=True,force_rebalance=False):
    config={'tickers':sorted([str(x).upper() for x in (tickers or [])]),'period':period,'limit':int(limit),
            'train_days':int(train_days),'test_days':int(test_days),'purge_days':int(purge_days),'embargo_days':int(embargo_days),
            'one_way_cost_bps':float(one_way_cost_bps),'rebalance_every':int(rebalance_every),
            'portfolio_value':float(portfolio_value),'adv_limit_pct':float(adv_limit_pct)}
    ch=_hash(config);pit=pit_universe_status()
    validation=purged_walk_forward_cost_reality(
        tickers or None,period,int(limit),int(train_days),int(test_days),int(purge_days),int(embargo_days),
        int(one_way_cost_bps),int(rebalance_every),float(portfolio_value),float(adv_limit_pct))
    reasons=[]
    if validation.get('status')!='OK':reasons.append('VALIDATION_NOT_READY')
    if validation.get('status')=='OK' and float(validation.get('net_mean_spread_5d') or 0)<=0:reasons.append('NET_EDGE_NOT_POSITIVE')
    rebs=max(1,int(validation.get('rebalances') or 0))
    cap_rate=float(validation.get('capacity_flagged_rebalances') or 0)/rebs
    if validation.get('status')=='OK' and cap_rate>.40:reasons.append('CAPACITY_FAILURE_RATE_HIGH')
    if reasons:
        out={'status':'RESEARCH_ONLY','config_hash':ch,'reasons':reasons,'validation':validation,
             'pit_universe':pit,'tournament_id':None,
             'policy':'Failed research stages cannot be bypassed. No live execution path exists.'}
        with closing(_conn()) as c, c:
            c.execute('INSERT OR IGNORE INTO experiments(config_hash,created_epoch,tournament_id,status,config_json) VALUES(?,?,?,?,?)',
                      (ch,time.time(),None,'RESEARCH_ONLY',json.dumps(config,sort_keys=True)))
        _save_run(ch,'RESEARCH_ONLY',out);return out

    exp=_existing(ch);tid=(exp or {}).get('tournament_id')
    if tid is None and auto_create_paper:
        created=xs_tournament.create(float(portfolio_value),'XU100');tid=created.get('tournament_id')
        if tid:
            xs_tournament.start(tid)
            xs_scheduler.configure(tid,enabled=True,rebalance_every_days=int(rebalance_every),
                                   cost_bps=float(one_way_cost_bps),limit=int(limit),adv_limit_pct=float(adv_limit_pct))
            with closing(_conn()) as c, c:
                c.execute('INSERT OR REPLACE INTO experiments(config_hash,created_epoch,tournament_id,status,config_json) VALUES(?,?,?,?,?)',
                          (ch,time.time(),int(tid),'PAPER_INCUBATION',json.dumps(config,sort_keys=True)))
    if tid is None:
        out={'status':'PAPER_ELIGIBLE','config_hash':ch,'validation':validation,'pit_universe':pit,
             'tournament_id':None,'policy':'Research passed implementation reality; paper tournament creation is disabled.'}
        _save_run(ch,'PAPER_ELIGIBLE',out);return out

    cycle=xs_scheduler.run_once(int(tid),force_rebalance=bool(force_rebalance))
    snap=xs_tournament.snapshot(int(tid))
    review=[x for x in (snap.get('challengers') or []) if (x.get('forward_scorecard') or {}).get('status')=='ELIGIBLE_FOR_REVIEW']
    status='PROMOTION_REVIEW' if review else 'PAPER_INCUBATION'
    out={'status':status,'config_hash':ch,'validation':validation,'pit_universe':pit,'tournament_id':int(tid),
         'paper_cycle':cycle,'eligible_challengers':[{'id':x.get('id'),'portfolio_id':x.get('portfolio_id')} for x in review],
         'tournament':{'days':snap.get('days'),'paper_champion':snap.get('paper_champion'),
                       'ranking':(snap.get('meta_governance') or {}).get('ranking')},
         'policy':'Autonomous research loop is paper-only. Promotion review is a research label and never authorizes production/live execution.'}
    _save_run(ch,status,out);return out

def status(limit=50):
    with closing(_conn()) as c, c:
        c.row_factory=sqlite3.Row
        ex=[dict(x) for x in c.execute('SELECT * FROM experiments ORDER BY created_epoch DESC LIMIT ?',(max(1,min(int(limit),200)),)).fetchall()]
        runs=[dict(x) for x in c.execute('SELECT id,config_hash,created_epoch,status FROM runs ORDER BY id DESC LIMIT ?',(max(1,min(int(limit),200)),)).fetchall()]
    return {'status':'OK','experiments':ex,'runs':runs,
            'policy':'Paper/research orchestration only; no broker or live execution authority.'}
