"""V55 prospective XS paper tournament.
Creates equal-capital challenger portfolios and ranks only forward paper evidence.
No live broker path and no backtest-only promotion.
"""
from __future__ import annotations
import json, sqlite3, threading, time
from pathlib import Path
from . import xs_paper
from .meta_governance import conservative_score, meta_decision
from .champion_governance import evaluate as champion_governance_evaluate
from .forward_scorecard import build as forward_scorecard

_LOCK=threading.RLock()

VARIANTS=[
 {'id':'xs_equal','name':'XS Equal Weight','method':'equal'},
 {'id':'xs_inverse_vol','name':'XS Inverse Vol','method':'inverse_vol'},
 {'id':'xs_score_inverse_vol','name':'XS Score × Inverse Vol','method':'score_inverse_vol'},
]

def _db():
    p=Path.home()/'.bist-ai-terminal'/'xs_tournament.db'
    p.parent.mkdir(parents=True,exist_ok=True)
    return p

def _conn():
    c=sqlite3.connect(_db())
    c.execute('''CREATE TABLE IF NOT EXISTS tournaments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_epoch REAL, created_at TEXT,
      started_epoch REAL, started_at TEXT, capital_each REAL, benchmark TEXT, champion TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS challengers(
      tournament_id INTEGER, variant_id TEXT, name TEXT, method TEXT, portfolio_id INTEGER,
      PRIMARY KEY(tournament_id,variant_id)
    )''')
    c.commit();return c

def create(capital_each=1_000_000,benchmark='XU100'):
    now=time.time();cap=max(10000,float(capital_each))
    with _LOCK:
        c=_conn();cur=c.execute('INSERT INTO tournaments(created_epoch,created_at,capital_each,benchmark,champion) VALUES(?,?,?,?,?)',
            (now,time.strftime('%d.%m.%Y %H:%M:%S'),cap,benchmark,None))
        tid=cur.lastrowid
        created=[]
        for v in VARIANTS:
            p=xs_paper.create('XS Tournament · '+v['name'],cap,benchmark)
            pid=p['portfolio_id']
            c.execute('INSERT INTO challengers(tournament_id,variant_id,name,method,portfolio_id) VALUES(?,?,?,?,?)',
                (tid,v['id'],v['name'],v['method'],pid))
            created.append({**v,'portfolio_id':pid})
        c.commit();c.close()
    return {'status':'OK','tournament_id':tid,'challengers':created}

def start(tournament_id):
    now=time.time()
    with _LOCK:
        c=_conn();r=c.execute('SELECT started_epoch FROM tournaments WHERE id=?',(int(tournament_id),)).fetchone()
        if not r:c.close();return {'status':'NOT_FOUND'}
        if r[0] is None:
            c.execute('UPDATE tournaments SET started_epoch=?,started_at=? WHERE id=?',
                      (now,time.strftime('%d.%m.%Y %H:%M:%S'),int(tournament_id)));c.commit()
        c.close()
    return snapshot(tournament_id)

def rebalance_variant(tournament_id,variant_id,rows,one_way_cost_bps=20,lineage=None):
    with _LOCK:
        c=_conn();r=c.execute('SELECT portfolio_id FROM challengers WHERE tournament_id=? AND variant_id=?',
            (int(tournament_id),str(variant_id))).fetchone();c.close()
    if not r:return {'status':'NOT_FOUND'}
    return xs_paper.rebalance(int(r[0]),rows,one_way_cost_bps,lineage)

def mark_all(tournament_id):
    with _LOCK:
        c=_conn();rows=c.execute('SELECT variant_id,portfolio_id FROM challengers WHERE tournament_id=?',(int(tournament_id),)).fetchall();c.close()
    if not rows:return {'status':'NOT_FOUND'}
    out=[]
    for vid,pid in rows:
        out.append({'variant_id':vid,**xs_paper.mark(int(pid))})
    return {'status':'OK','rows':out}

def _metrics(h,days):
    p=h['portfolio'];curve=list(reversed(h.get('curve') or []));rebs=h.get('rebalances') or []
    capital=float(p['capital']);equity=float(p['last_equity'])
    ret=(equity/capital-1)*100 if capital else 0
    maxdd=max([abs(float(x.get('drawdown_pct') or 0)) for x in curve],default=0)
    excess=float(curve[-1].get('excess_pct') or 0) if curve else 0
    costs=sum(float(x.get('cost') or 0) for x in rebs)
    # Rebalance count is the closest portfolio-level analogue to closed trades.
    m={'return_pct':ret,'max_drawdown_pct':maxdd,'closed_trades':len(rebs),'profit_factor':1.0 if ret>=0 else 0.5,'fees_paid':costs}
    score=conservative_score(m,days)
    reasons=[]
    if days<90:reasons.append('MIN_90_DAYS')
    if len(rebs)<12:reasons.append('MIN_12_REBALANCES')
    if maxdd>8:reasons.append('DRAWDOWN')
    if excess<=0:reasons.append('NO_BENCHMARK_EXCESS')
    return {'return_pct':round(ret,4),'excess_pct':round(excess,4),'max_drawdown_pct':round(maxdd,4),
            'rebalance_count':len(rebs),'costs_paid':round(costs,2),'score':score,
            'status':'ELIGIBLE' if not reasons else 'OBSERVE','reasons':reasons}

def snapshot(tournament_id):
    with _LOCK:
        c=_conn();t=c.execute('SELECT * FROM tournaments WHERE id=?',(int(tournament_id),)).fetchone()
        if not t:c.close();return {'status':'NOT_FOUND'}
        cols=[x[1] for x in c.execute('PRAGMA table_info(tournaments)').fetchall()]
        td=dict(zip(cols,t))
        ch=c.execute('SELECT variant_id,name,method,portfolio_id FROM challengers WHERE tournament_id=?',(int(tournament_id),)).fetchall();c.close()
    days=max(0,int((time.time()-float(td['started_epoch']))/86400)) if td.get('started_epoch') else 0
    rows=[]
    for vid,name,method,pid in ch:
        h=xs_paper.history(int(pid),500)
        scorecard=forward_scorecard(h,days,max(1,len(ch)))
        details=scorecard.get('details') or {}
        promo=details.get('promotion_gate') or {'status':'NOT_RUN','reasons':['SCORECARD_DETAIL_MISSING']}
        stats=details.get('statistical_gate') or {'status':'NOT_RUN','reasons':['SCORECARD_DETAIL_MISSING']}
        regime=details.get('regime_gate') or {'status':'NOT_RUN','reasons':['SCORECARD_DETAIL_MISSING']}
        quality=details.get('data_quality_gate') or {'status':'NOT_RUN','reasons':['SCORECARD_DETAIL_MISSING']}
        factor=details.get('factor_gate') or {'status':'NOT_RUN','reasons':['SCORECARD_DETAIL_MISSING']}
        stress=details.get('portfolio_stress_gate') or {'status':'NOT_RUN','reasons':['SCORECARD_DETAIL_MISSING']}
        decay=details.get('decay_v2') or {'status':'UNKNOWN'}
        metrics=_metrics(h,days)
        eligible=scorecard.get('status')=='ELIGIBLE_FOR_REVIEW'
        metrics['status']='ELIGIBLE' if eligible else 'OBSERVE'
        decay_reasons=['MODEL_DECAY'] if decay.get('status')=='DECAY' else []
        metrics['reasons']=list(dict.fromkeys((promo.get('reasons') or [])+(stats.get('reasons') or [])+(regime.get('reasons') or [])+(quality.get('reasons') or [])+(factor.get('reasons') or [])+(stress.get('reasons') or [])+decay_reasons))
        rows.append({'id':vid,'name':name,'method':method,'portfolio_id':pid,'metrics':metrics,'promotion_gate':promo,'statistical_gate':stats,'regime_gate':regime,'data_quality_gate':quality,'factor_gate':factor,'portfolio_stress_gate':stress,'decay_v2':decay,'forward_scorecard':scorecard,'paper':h})
    ranking=[{'id':r['id'],'name':r['name'],'score':r['metrics']['score'],'status':r['metrics']['status'],'reasons':r['metrics']['reasons']} for r in rows]
    ranking.sort(key=lambda x:(x['status']!='ELIGIBLE',-x['score'],x['id']))
    legacy_decision=meta_decision(ranking,td.get('champion'))
    champion_gov=champion_governance_evaluate(tournament_id,rows,td.get('champion'))
    next_champion=(champion_gov.get('decision') or {}).get('paper_champion')
    if next_champion and next_champion!=td.get('champion') and (champion_gov.get('decision') or {}).get('action') in {'NOMINATE_PAPER_CHAMPION','ROTATE_PAPER_CHAMPION'}:
        with _LOCK:
            c=_conn();c.execute('UPDATE tournaments SET champion=? WHERE id=?',(str(next_champion),int(tournament_id)));c.commit();c.close()
        td['champion']=str(next_champion)
    return {'status':'OK','tournament_id':tournament_id,'started_at':td.get('started_at'),'days':days,
            'capital_each':td.get('capital_each'),'benchmark':td.get('benchmark'),'paper_champion':td.get('champion'),'challengers':rows,
            'meta_governance':{'ranking':ranking,'decision':legacy_decision,'legacy_decision':legacy_decision,'champion_governance':champion_gov},
            'policy':'Prospective paper evidence only. Paper champion is a research label; it never authorizes production or live execution.'}
