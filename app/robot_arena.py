"""Equal-policy, token-isolated prospective paper tournament. No broker imports/calls."""
from __future__ import annotations
import copy,json,math,os,threading,time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from . import auto_paper as paper
from .robot_strategies import CATALOG,catalog,entry,exit_reason

_LOCK=threading.RLock();_BUSY=set();_THREADS={}

def _directory():
    from .broker_bridge import _dir
    p=Path(os.getenv('BIST_ROBOT_ARENA_DIR') or _dir()/'robot-arena');p.mkdir(parents=True,exist_ok=True);return p
def _read(key):return json.loads((_directory()/(key+'.json')).read_text())
def _write(key,a):
    path=_directory()/(key+'.json');tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(a,ensure_ascii=False,allow_nan=False));os.chmod(tmp,0o600);os.replace(tmp,path)

def fresh():
    cfg={**paper.DEFAULTS,'allow_short':False}
    bots={}
    for b in CATALOG:
        a=paper.fresh();a.update({'strategy':b['id'],'strategy_version':1,'config':dict(cfg),'max_drawdown_pct':0.,'arena_stats':{'fees':0.,'closed':0,'wins':0,'profit':0.,'loss':0.}});bots[b['id']]=a
    return {'version':1,'created_at':paper.stamp(),'started_at':None,'enabled':False,'config':cfg,'bots':bots,'scan':{'cursor':0,'rows':{},'codes':[],'coverage_pct':0},'benchmark':{},'last_risk_check':None,'error':None}

def create(token):
    key=paper._key(token)
    with _LOCK:
        if not (_directory()/(key+'.json')).exists():_write(key,fresh())
    return snapshot(token)

def metrics(a):
    v=paper.valuation(a);exits=[o for o in a['orders'] if o.get('pnl') is not None];wins=[o['pnl'] for o in exits if o['pnl']>0];losses=[-o['pnl'] for o in exits if o['pnl']<0]
    stats=a.get('arena_stats',{'closed':len(exits),'wins':len(wins),'profit':sum(wins),'loss':sum(losses),'fees':sum(o['fee'] for o in a['orders'])})
    return {**v,'return_pct':round(v['total_pnl']/a['capital']*100,4),'max_drawdown_pct':round(a.get('max_drawdown_pct',0),4),'closed_trades':stats['closed'],'win_rate_pct':round(stats['wins']/stats['closed']*100,2) if stats['closed'] else None,'profit_factor':round(stats['profit']/stats['loss'],4) if stats['loss'] else None,'profit_factor_note':'Kayıplı kapanış yok; oran hesaplanmadı.' if not stats['loss'] else None,'fees_paid':round(stats['fees'],4),'stale_quotes':[c for c in a['positions'] if not paper.valid_quote(a['quotes'].get(c),paper.now_tr())],'borrow_cost':a['borrow_cost']}

def snapshot(token):
    key=paper._key(token)
    with _LOCK:
        try:a=_read(key)
        except FileNotFoundError:return {'exists':False,**catalog()}
    rows=[]
    for b in CATALOG:
        bot=a['bots'][b['id']];rows.append({**b,'metrics':metrics(bot),'positions':paper.valuation(bot)['positions'],'pending':list(bot['pending'].values()),'orders':bot['orders'][:200],'decisions':bot['decisions'][:100],'curve':bot['curve'][-500:],'risk_halt':bot['risk_halt'],'quote_errors':bot.get('quote_errors',{}),'created_at':bot['created_at']})
    rows.sort(key=lambda r:(-r['metrics']['return_pct'],r['metrics']['max_drawdown_pct'],r['id']))
    scan={k:v for k,v in a['scan'].items() if k not in {'rows','codes'}};scan['total']=len(a['scan']['codes'])
    bench=a['benchmark'];ret=(bench['last']['close']/bench['base']['close']-1)*100 if bench.get('base') and bench.get('last') else None
    return {'exists':True,'mode':'FORWARD_PAPER','live_execution':False,'validation':'UNVALIDATED','enabled':a['enabled'],'started_at':a['started_at'],'created_at':a['created_at'],'config':a['config'],'scan':scan,'last_risk_check':a['last_risk_check'],'error':a['error'],'benchmark':{'return_pct':ret,'cash_adjusted_pct':ret*a['config']['gross_pct']/100 if ret is not None else None,'base_at':bench.get('base',{}).get('at'),'last_at':bench.get('last',{}).get('at'),'label':'XU100 fiyat endeksi · masrafsız referans, temettü ve nakit faizi hariç; doğrudan alınabilir ürün değil'},'bots':rows,'external':catalog()['external'],'adaptation':catalog()['adaptation'],'worker_running':all(_THREADS.get(l) and _THREADS[l].is_alive() for l in ('scan','risk'))}

def configure(token,payload):
    key=paper._key(token)
    with _LOCK:
        a=_read(key)
        if a['started_at']:raise ValueError('Deney başladı; adil karşılaştırma için ortak ayarlar kilitli.')
        for k,v in payload.items():
            if k=='allow_short':
                if type(v) is not bool:raise ValueError('Sanal açığa satış seçimi geçersiz.')
            elif k in {'fee_bps','slippage_bps'}:
                if type(v) not in (int,float) or not math.isfinite(v) or not (0 if k=='fee_bps' else 1)<=v<=100:raise ValueError('Masraf 0–100, kayma 1–100 baz puan aralığında olmalı.')
            else:raise ValueError('Yalnız ortak komisyon, kayma ve sanal açığa satış ayarlanabilir.')
        a['config'].update(payload)
        for b in a['bots'].values():b['config']=dict(a['config'])
        _write(key,a)
    return snapshot(token)

def control(token,action):
    key=paper._key(token)
    with _LOCK:
        a=_read(key);now=paper.now_tr()
        if action=='start':
            a['enabled']=True;a['started_at']=a['started_at'] or now.isoformat();a['scan'].update({'next_due':0,'retry_at':0})
        elif action in {'pause','close_all'}:a['enabled']=False
        else:raise ValueError('Geçersiz kontrol; canlı işlem veya deney sıfırlama desteklenmez.')
        for bot in a['bots'].values():
            bot['enabled']=a['enabled']
            if not a['enabled']:bot['pending']={c:o for c,o in bot['pending'].items() if o['side'] in {'SELL','COVER'}}
            if action=='close_all':
                for c,p in bot['positions'].items():paper.queue(bot,c,'SELL' if p['quantity']>0 else 'COVER','Laboratuvar: tümünü kapat ve durdur.',now)
            paper.event(bot,'CONTROL','',action+' · ortak deney kontrolü')
        _write(key,a)
    start_worker();return snapshot(token)

def apply_scan(a,rows,requested,now):
    from .market_data import daily_epoch
    valid=[r for r in rows if r.get('as_of')==daily_epoch(now)]
    coverage=len(valid)/max(1,requested)*100;a['scan']['coverage_pct']=round(coverage,1)
    feature_rows=[r for r in valid if isinstance(r.get('robot_features',{}).get('ema50_bull'),bool)]
    breadth=sum(r['robot_features']['ema50_bull'] for r in feature_rows)/len(feature_rows)*100 if feature_rows and len(feature_rows)/max(1,requested)*100>=a['config']['min_coverage_pct'] else None
    for r in valid:r.setdefault('robot_features',{})['breadth_pct']=breadth
    a['scan']['breadth_pct']=breadth
    for sid,bot in a['bots'].items():
        paper.choose(bot,valid,requested,now,signal_fn=lambda r,s=sid:entry(s,r),exit_fn=lambda r,p,s=sid:exit_reason(s,r,p))

def cycle(key,now=None,lane='scan'):
    if lane not in {'scan','risk'}:raise ValueError('Geçersiz hat')
    fixed=now is not None;now=now or paper.now_tr();requested_at=now.isoformat();busy=(key,lane)
    with _LOCK:
        if busy in _BUSY:return
        a=_read(key);_BUSY.add(busy)
    try:
        if lane=='scan':
            if not a['enabled']:return
            from .universe import get_universe
            from .market_data import daily_epoch
            u=get_universe()
            if not u or any(r.get('source')!='KAP' for r in u):raise ValueError('KAP evreni yok; yedek evrenle karşılaştırma yapılmaz.')
            codes=list(dict.fromkeys(r['ticker'] for r in u));epoch=daily_epoch(now);scan=a['scan'];offset=scan['cursor'] if scan['codes']==codes and scan.get('epoch')==epoch else 0;batch=codes[offset:offset+20]
            rows=paper.closed_signals(batch,now,enrich=True)
            if not fixed:now=paper.now_tr()
            with _LOCK:
                a=_read(key)
                if not a['enabled']:return
                s=a['scan']
                if s['codes']!=codes or s.get('epoch')!=epoch:s.update({'codes':codes,'cursor':0,'rows':{},'epoch':epoch})
                if s['cursor']!=offset:return
                if offset==0:s['started_at']=requested_at
                s['rows'].update({r['ticker']:r for r in rows});s['cursor']+=len(batch);s['last_batch_at']=now.isoformat();s['retry_at']=0;a['error']=None
                if s['cursor']>=len(codes):
                    apply_scan(a,list(s['rows'].values()),len(codes),now)
                    s.update({'cursor':0,'rows':{},'completed_count':len(codes),'completed_at':now.isoformat(),'next_due':now.timestamp()+600,'duration_sec':round((now-datetime.fromisoformat(s['started_at'])).total_seconds(),1)})
                _write(key,a)
        else:
            codes=set().union(*(set(b['positions'])|set(b['pending']) for b in a['bots'].values()))
            if a['started_at']:codes.add('XU100')
            def quote(c):
                try:return c,paper.latest_quote(c,now)
                except Exception:return c,None
            with ThreadPoolExecutor(max_workers=3) as ex:quotes=dict(ex.map(quote,sorted(codes)))
            if not fixed:now=paper.now_tr()
            with _LOCK:
                a=_read(key)
                for b in a['bots'].values():
                    paper.risk_check(b,now)
                    for c in sorted(set(b['positions'])|set(b['pending'])):
                        if quotes.get(c):paper.process_quote(b,c,quotes[c],now);paper.risk_check(b,now)
                    v=paper.risk_check(b,now);b['max_drawdown_pct']=max(b.get('max_drawdown_pct',0),max(0,(1-v['equity']/b['peak'])*100))
                    b['curve'].append({'time':now.isoformat(),'equity':v['equity']});b['curve']=b['curve'][-2000:];b['last_risk_check']=now.isoformat()
                q=quotes.get('XU100')
                if a['started_at'] and q and paper.valid_quote(q,now) and datetime.fromisoformat(q['start'])>=datetime.fromisoformat(a['started_at']):
                    bench=a['benchmark'];prev=bench.get('last',{})
                    if not prev or q['at']>prev['at']:
                        if not bench.get('base'):bench['base']=q
                        bench['last']=q
                a['last_risk_check']=now.isoformat();_write(key,a)
    except Exception as e:
        with _LOCK:
            a=_read(key);a['error']=str(e)[:250]
            if lane=='scan':a['scan']['retry_at']=now.timestamp()+30
            _write(key,a)
    finally:
        with _LOCK:_BUSY.discard(busy)

def _loop(lane):
    while True:
        try:
            for path in list(_directory().glob('*.json')):
                try:
                    with _LOCK:a=_read(path.stem)
                    now=paper.now_tr()
                    if lane=='scan':
                        if not paper.scan_due(a,now):continue
                    else:
                        if not(a['started_at'] or any(b['positions'] or b['pending'] for b in a['bots'].values())):continue
                        last=a['last_risk_check']
                        if last and now.timestamp()-datetime.fromisoformat(last).timestamp()<30:continue
                    cycle(path.stem,lane=lane)
                except Exception:continue
        except Exception:pass
        time.sleep(1)

def start_worker():
    with _LOCK:
        for lane in ('scan','risk'):
            if not(_THREADS.get(lane) and _THREADS[lane].is_alive()):
                _THREADS[lane]=threading.Thread(target=_loop,args=(lane,),daemon=True,name='RobotArena-'+lane);_THREADS[lane].start()
