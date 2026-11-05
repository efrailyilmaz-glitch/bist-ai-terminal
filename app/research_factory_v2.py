"""V116 Continuous Research Factory.
Adds integrity preflight, durable run ledger and research-stage orchestration around the existing
autonomous research loop. It can create/advance paper challengers but has no production/live authority.
"""
from __future__ import annotations
import hashlib,json,sqlite3,time
from pathlib import Path
from .runtime_db import connect as db_connect
from .data_provider_trust_v2 import snapshot as data_trust
from .pit_universe import dataset_status as pit_status
from .feature_governance_v3 import report as feature_governance
from .research_integrity_dashboard import dashboard as integrity_dashboard
from .autonomous_research_loop import run_once as research_run

def _db():
    p=Path.home()/'.bist-ai-terminal'/'research_factory_v2.db'
    p.parent.mkdir(parents=True,exist_ok=True);return p

def _conn():
    c=db_connect(_db())
    c.execute('''CREATE TABLE IF NOT EXISTS factory_runs(
      id INTEGER PRIMARY KEY AUTOINCREMENT, run_hash TEXT, created_epoch REAL,
      stage TEXT, status TEXT, config_json TEXT, result_json TEXT
    )''')
    c.commit();return c

def _hash(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def run_once(config=None):
    cfg=dict(config or {})
    codes=[str(x).upper().replace('.IS','') for x in (cfg.get('tickers') or []) if str(x).strip()]
    trust=data_trust(codes[:100])
    pit=pit_status()
    feat=feature_governance(20,30)
    integ=integrity_dashboard()
    blockers=[]
    if trust.get('status')=='DATA_BLOCK' or not trust.get('decision_allowed'):blockers.append('DATA_TRUST_BLOCK')
    if pit.get('status') not in {'PIT_VERIFIED','PARTIAL'}:blockers.append('PIT_UNIVERSE_NOT_READY')
    if integ.get('status')=='BLOCK':blockers.append('RESEARCH_INTEGRITY_BLOCK')
    leakage=sum(1 for x in (feat.get('rows') or []) if x.get('state')=='LEAKAGE_RISK_BLOCK')
    if leakage: blockers.append('FEATURE_LINEAGE_BLOCK')
    run_hash=_hash({'cfg':cfg,'preflight':{'trust':trust.get('status'),'pit':pit.get('status'),'integrity':integ.get('status'),'leakage':leakage}})
    if blockers:
        out={'status':'PREFLIGHT_BLOCK','version':'116.0','run_hash':run_hash,'blockers':blockers,
             'preflight':{'data_trust':trust,'pit_universe':pit,'feature_governance':{'summary':feat.get('summary')},'research_integrity':integ},
             'live_execution':False,'policy':'Research factory preflight blocks before validation/paper creation. No stage can bypass integrity blockers.'}
        with _conn() as c:c.execute('INSERT INTO factory_runs(run_hash,created_epoch,stage,status,config_json,result_json) VALUES(?,?,?,?,?,?)',
            (run_hash,time.time(),'PREFLIGHT',out['status'],json.dumps(cfg,sort_keys=True),json.dumps(out,ensure_ascii=False,default=str)))
        return out
    args={
      'tickers':codes or None,'period':str(cfg.get('period') or '5y'),'limit':int(cfg.get('limit') or 120),
      'train_days':int(cfg.get('train_days') or 252),'test_days':int(cfg.get('test_days') or 63),
      'purge_days':int(cfg.get('purge_days') or 5),'embargo_days':int(cfg.get('embargo_days') or 5),
      'one_way_cost_bps':int(cfg.get('one_way_cost_bps') or 20),'rebalance_every':int(cfg.get('rebalance_every') or 5),
      'portfolio_value':float(cfg.get('portfolio_value') or 1_000_000),'adv_limit_pct':float(cfg.get('adv_limit_pct') or 1.0),
      'auto_create_paper':bool(cfg.get('auto_create_paper',True)),'force_rebalance':bool(cfg.get('force_rebalance',False))
    }
    result=research_run(**args)
    stage='PAPER' if result.get('tournament_id') else 'VALIDATION'
    out={'status':result.get('status'),'version':'116.0','run_hash':run_hash,'stage':stage,
         'preflight':{'data_trust':{'status':trust.get('status'),'trust_score':trust.get('trust_score')},
                      'pit_universe':{'status':pit.get('status')},
                      'feature_governance':{'summary':feat.get('summary')},
                      'research_integrity':{'status':integ.get('status')}},
         'research_loop':result,'live_execution':False,
         'policy':'Continuous research factory may validate and incubate paper challengers only. Production champion and broker/live execution remain outside its authority.'}
    with _conn() as c:c.execute('INSERT INTO factory_runs(run_hash,created_epoch,stage,status,config_json,result_json) VALUES(?,?,?,?,?,?)',
        (run_hash,time.time(),stage,str(out['status']),json.dumps(cfg,sort_keys=True),json.dumps(out,ensure_ascii=False,default=str)))
    return out

def status(limit=50):
    with _conn() as c:
        c.row_factory=sqlite3.Row
        rows=[dict(x) for x in c.execute('SELECT id,run_hash,created_epoch,stage,status,config_json FROM factory_runs ORDER BY id DESC LIMIT ?',(max(1,min(int(limit),200)),)).fetchall()]
    return {'status':'OK','version':'116.0','runs':rows,'live_execution':False,
            'policy':'Factory history is an inspectable research ledger; no run can auto-promote or place orders.'}
