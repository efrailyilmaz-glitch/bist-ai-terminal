"""Account-isolated forward paper trading. Never calls a broker or submits real orders."""
from __future__ import annotations
import copy, hashlib, json, math, os, re, secrets, threading, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

TR=ZoneInfo('Europe/Istanbul')
DEFAULTS={'max_positions':6,'position_pct':10.,'gross_pct':60.,'risk_pct':.5,'daily_loss_pct':2.,'drawdown_pct':10.,'fee_bps':10.,'slippage_bps':10.,'borrow_annual_pct':15.,'min_coverage_pct':80.,'allow_short':True}
_LOCK=threading.RLock();_BUSY=set();_THREAD=None;_RISK_THREAD=None

def now_tr():return datetime.now(TR)
def stamp():return now_tr().isoformat()
def fresh(capital=1_000_000.):
    return {'version':1,'strategy':'CLOSED_DAILY_TREND_V1','capital':capital,'cash':capital,'realized':0.,'borrow_cost':0.,'enabled':False,'config':dict(DEFAULTS),'positions':{},'pending':{},'quotes':{},'orders':[],'decisions':[],'curve':[],'scan':{'cursor':0,'rows':{},'codes':[],'coverage_pct':0.},'last_cycle':None,'error':None,'risk_halt':None,'day':None,'day_equity':capital,'peak':capital,'last_equity':capital,'created_at':stamp()}

def event(a,kind,ticker,reason,**extra):
    a['decisions'].insert(0,{'id':secrets.token_hex(8),'time':stamp(),'type':kind,'ticker':ticker,'reason':reason,**extra});del a['decisions'][1000:]

def valuation(a):
    total=a['cash'];unreal=0.;gross=0.;rows=[];missing=[]
    for code,p in a['positions'].items():
        q=a['quotes'].get(code) or {};px=q.get('close');valid=isinstance(px,(float,int)) and math.isfinite(px) and px>0
        if not valid:missing.append(code);px=p['avg']
        n=abs(p['quantity']);value=n*px if p['quantity']>0 else n*(2*p['avg']-px)
        pnl=(px-p['avg'])*p['quantity']-p['fees'];total+=value;unreal+=pnl;gross+=n*px
        rows.append({'ticker':code,**p,'price':px,'as_of':q.get('at'),'pnl':round(pnl,2),'quote_missing':not valid})
    return {'equity':round(total,2),'cash':round(a['cash'],2),'unrealized':round(unreal,2),'realized':round(a['realized'],2),'total_pnl':round(total-a['capital'],2),'gross':round(gross,2),'positions':rows,'missing':missing,'valuation':'LAST_OBSERVED_DELAYED_BAR'}

def signal(r):
    """Symmetric, fixed rules; guarded cap scores never constitute a buy signal."""
    if r.get('signal_guard',{}).get('status')!='CLEAR' or r.get('trap_defense',{}).get('status')!='CLEAR' or r.get('bar_provisional') or r.get('history_bars',0)<200:return None
    if not all(isinstance(r.get(k),(int,float)) and math.isfinite(r[k]) for k in ['short_score','long_score','adx','rsi','atr','price','avg_value_turnover_20']):return None
    if r['avg_value_turnover_20']<10_000_000 or r.get('risk',100)>=80 or r['atr']<=0:return None
    if r['short_score']>=75 and r['long_score']>=68 and r.get('supertrend')=='BULLISH' and r.get('macd_hist',0)>0 and r['adx']>=22 and 45<=r['rsi']<=72:
        return ('BUY','Kapanmış günlük bar: kısa ≥75, uzun ≥68, MACD pozitif, Supertrend yukarı, ADX ≥22, RSI 45–72.',r['short_score'])
    if r['short_score']<=30 and r['long_score']<=40 and r.get('supertrend')=='BEARISH' and r.get('macd_hist',0)<0 and r['adx']>=25 and 28<=r['rsi']<=55:
        return ('SHORT','Kapanmış günlük bar: kısa ≤30, uzun ≤40, MACD negatif, Supertrend aşağı, ADX ≥25, RSI 28–55.',100-r['short_score'])
    return None

def queue(a,code,side,reason,now,**extra):
    if code in a['pending']:return
    a['pending'][code]={'id':secrets.token_hex(10),'ticker':code,'side':side,'reason':reason,'created_at':now.isoformat(),**extra}
    event(a,'QUEUED',code,reason,side=side)

def fill(a,o,reference,at,quantity=None):
    code=o['ticker'];side=o['side'];cfg=a['config'];qty=int(quantity if quantity is not None else o.get('quantity',abs(a['positions'].get(code,{}).get('quantity',0))))
    buy=side in {'BUY','COVER'};px=reference*(1+(1 if buy else -1)*cfg['slippage_bps']/10000);fee=qty*px*cfg['fee_bps']/10000
    if not math.isfinite(px) or px<=0 or qty<1:raise ValueError('Geçersiz sanal dolum')
    pnl=None
    if side in {'BUY','SHORT'}:
        if code in a['positions'] or qty*px+fee>a['cash']:raise ValueError('Nakit/teminat veya açık pozisyon sınırı')
        signed=qty if side=='BUY' else -qty;distance=o['stop_distance']
        a['cash']-=qty*px+fee
        a['positions'][code]={'quantity':signed,'avg':px,'fees':fee,'opened_at':at,'entry_bar':at,'stop':px-distance if signed>0 else px+distance,'target':px+2*distance if signed>0 else px-2*distance,'reason':o['reason']}
    else:
        p=a['positions'][code];qty=abs(p['quantity']);fee=qty*px*cfg['fee_bps']/10000
        pnl=(px-p['avg'])*p['quantity']-p['fees']-fee
        a['cash']+=qty*px-fee if p['quantity']>0 else qty*(2*p['avg']-px)-fee
        a['realized']+=pnl;del a['positions'][code]
    order={'id':o['id'],'time':at,'recorded_at':stamp(),'ticker':code,'side':side,'quantity':qty,'price':round(px,6),'reference_price':reference,'fee':round(fee,6),'pnl':None if pnl is None else round(pnl,6),'reason':o['reason'],'mode':'PAPER','source':'DELAYED_15M_CLOSED_BAR'}
    stats=a.get('arena_stats')
    if stats is not None:
        stats['fees']+=fee
        if pnl is not None:
            stats['closed']+=1;stats['wins']+=int(pnl>0);stats['profit']+=max(0,pnl);stats['loss']+=max(0,-pnl)
    a['orders'].insert(0,order);del a['orders'][2000:];event(a,'FILLED',code,o['reason'],side=side)

def valid_quote(q,now):
    try:
        end=datetime.fromisoformat(q['at']);start=datetime.fromisoformat(q['start'])
        vals=[float(q[k]) for k in ['open','high','low','close','volume']]
        return start.tzinfo is not None and end.tzinfo is not None and now.weekday()<5 and start.astimezone(TR).date()==now.date() and start.astimezone(TR).hour>=10 and end.astimezone(TR).hour<=18 and 0<=(now-end).total_seconds()<=45*60 and start<end and all(math.isfinite(v) for v in vals) and min(vals[:4])>0 and vals[4]>0 and q['high']>=max(q['open'],q['close'],q['low']) and q['low']<=min(q['open'],q['close'],q['high'])
    except (ValueError,KeyError,TypeError):return False

def process_quote(a,code,q,now):
    if not valid_quote(q,now):return
    old=a['quotes'].get(code)
    if old and q['at']<=old['at']:return
    if old and abs(q['close']/old['close']-1)>.25:
        errors=a.setdefault('quote_errors',{})
        if errors.get(code)!=q['at']:event(a,'DATA_HALT',code,'Fiyat ölçeğinde %25 üzeri değişim; kurumsal işlem/veri kontrolü gerekli. Dolum yapılmadı.')
        errors[code]=q['at'];return
    a.setdefault('quote_errors',{}).pop(code,None)
    a['quotes'][code]=q;p=a['positions'].get(code)
    # Existing protective exits first. A new entry cannot hit a stop in its own fill bar.
    if p and q['at']>p['entry_bar']:
        long=p['quantity']>0;stop=q['low']<=p['stop'] if long else q['high']>=p['stop'];target=q['high']>=p['target'] if long else q['low']<=p['target']
        if stop or target:
            px=(min(q['open'],p['stop']) if long else max(q['open'],p['stop'])) if stop else p['target']
            o={'id':secrets.token_hex(10),'ticker':code,'side':'SELL' if long else 'COVER','reason':'STOP · aynı barda iki seviye de varsa stop önce varsayılır' if stop else 'KÂR HEDEFİ'}
            fill(a,o,px,q['at']);a['pending'].pop(code,None);return
    o=a['pending'].get(code)
    if not o:return
    # Price must come from a complete bar starting AFTER the decision was recorded.
    if datetime.fromisoformat(q['start'])<datetime.fromisoformat(o['created_at']):return
    if o['side'] in {'SELL','COVER'}:
        if code in a['positions']:fill(a,o,q['close'],q['at'])
        a['pending'].pop(code,None);return
    if not a['enabled'] or a['risk_halt']:a['pending'].pop(code,None);return
    if (now-datetime.fromisoformat(o['created_at'])).total_seconds()>48*3600:
        a['pending'].pop(code,None);event(a,'CANCELLED',code,'Karar 48 saatten eski; yeni analiz gerekli.');return
    v=valuation(a);cfg=a['config'];px=q['close'];distance=max(o['atr']*2,px*.02)
    existing=[x for x in a['positions'] if x not in a['quotes'] or not valid_quote(a['quotes'][x],now)]
    room=max(0,v['equity']*cfg['gross_pct']/100-v['gross'])
    budget=min(max(0,v['equity'])*cfg['position_pct']/100,room,a['cash']/(1+(cfg['fee_bps']+cfg['slippage_bps'])*.0001))
    planned_loss=distance+px*(2*cfg['fee_bps']+2*cfg['slippage_bps'])/10000
    qty=math.floor(min(budget/(px*(1+cfg['slippage_bps']/10000)),max(0,v['equity'])*cfg['risk_pct']/100/planned_loss,q['volume']*.01))
    if existing or a.get('quote_errors') or distance>=px*.45 or len(a['positions'])>=cfg['max_positions'] or qty<1 or (o['side']=='SHORT' and not cfg['allow_short']):
        a['pending'].pop(code,None);event(a,'REJECTED',code,'Pozisyon/nakit/likidite sınırı veya eksik güncel fiyat.');return
    o['stop_distance']=distance;fill(a,o,px,q['at'],qty);a['pending'].pop(code,None)

def risk_check(a,now):
    v=valuation(a);day=str(now.date())
    if a['day']!=day:
        # Charge short borrow by elapsed calendar days, not poll count.
        if a['day']:
            days=(now.date()-datetime.fromisoformat(a['day']).date()).days
            charge=sum(abs(p['quantity'])*p['avg'] for p in a['positions'].values())*a['config']['borrow_annual_pct']/100/365*max(0,days)
            a['cash']-=charge;a['realized']-=charge;a['borrow_cost']+=charge
        a['day']=day;a['day_equity']=a['last_equity']
        if a['risk_halt']=='DAILY_LOSS':a['risk_halt']=None
    v=valuation(a);a['peak']=max(a['peak'],v['equity'])
    halt='DRAWDOWN' if v['equity']<=a['peak']*(1-a['config']['drawdown_pct']/100) else 'DAILY_LOSS' if v['equity']<=a['day_equity']*(1-a['config']['daily_loss_pct']/100) else None
    if halt:
        if a['risk_halt']!=halt:event(a,'RISK_HALT','',halt+' · yeni girişler durduruldu, pozisyon kapatma kuyruğu oluşturuldu.')
        a['risk_halt']=halt
        a['pending']={c:o for c,o in a['pending'].items() if o['side'] in {'SELL','COVER'}}
        for code,p in a['positions'].items():queue(a,code,'SELL' if p['quantity']>0 else 'COVER',halt,now)
    a['last_equity']=v['equity'];return v

def choose(a,rows,requested,now,signal_fn=None,exit_fn=None):
    from datetime import timedelta
    expected=now.date() if (now.hour,now.minute)>=(18,20) else now.date()-timedelta(days=1)
    while expected.weekday()>=5:expected-=timedelta(days=1)
    valid=[r for r in rows if r.get('as_of')==expected.isoformat()]
    coverage=len(valid)/max(1,requested)*100;a['scan']['coverage_pct']=round(coverage,1)
    if not a['enabled']:return
    for r in valid:
        code=r['ticker'];p=a['positions'].get(code)
        if p and (exit_fn(r,p) if exit_fn else ((p['quantity']>0 and r.get('supertrend')=='BEARISH') or (p['quantity']<0 and r.get('supertrend')=='BULLISH'))):
            queue(a,code,'SELL' if p['quantity']>0 else 'COVER','Kapanmış günlük barda trend tersine döndü.',now)
    if coverage<a['config']['min_coverage_pct']:
        event(a,'WAIT','','Yetersiz tarama kapsamı; yeni pozisyon açılmadı.',coverage_pct=round(coverage,1));return
    if a['risk_halt']:return
    candidates=[((signal_fn or signal)(r),r) for r in valid];candidates=[(s,r) for s,r in candidates if s and (s[0]!='SHORT' or a['config']['allow_short'])]
    candidates.sort(key=lambda x:(-x[0][2],x[1].get('risk',100),x[1]['ticker']))
    for s,r in candidates:
        if len(a['positions'])+sum(o['side'] in {'BUY','SHORT'} for o in a['pending'].values())>=a['config']['max_positions']:break
        code=r['ticker']
        if code in a['positions'] or code in a['pending']:continue
        # One decision per symbol and signal date, including rejected/closed trades.
        key=code+':'+r['as_of']
        if key in a.setdefault('signal_keys',[]):continue
        a['signal_keys']=(a['signal_keys']+[key])[-5000:]
        queue(a,code,s[0],s[1],now,atr=r['atr'],signal_as_of=r['as_of'])
    event(a,'SCAN_COMPLETE','','Kapalı bar stratejisi değerlendirildi.',coverage_pct=round(coverage,1),candidates=len(candidates))

def closed_signals(codes,now,enrich=False):
    import pandas as pd
    from .market_data import daily_frames,_ret
    from .scoring import score_frame
    from .signal_guard import daily_metadata
    frames=daily_frames(list(codes)+['XU100'])
    def closed(sym):
        df=frames.get(sym.removesuffix('.IS'),pd.DataFrame()).dropna(how='all')
        if df.empty:return df
        cutoff=now.date() if (now.hour,now.minute)>=(18,20) else (pd.Timestamp(now.date())-pd.Timedelta(days=1)).date()
        return df[[pd.Timestamp(i).date()<=cutoff for i in df.index]]
    bench=closed('XU100.IS');br20=_ret(bench,20) if len(bench)>20 else None;br60=_ret(bench,60) if len(bench)>60 else None
    out=[]
    for code in codes:
        try:
            df=closed(code+'.IS');r=score_frame(df,br20,br60)
            if not r:continue
            r=daily_metadata({'ticker':code,**r,'history_bars':len(df)},df.index[-1],now)
            if br20 is None or br60 is None:r['signal_guard']['status']='WAIT'
            if enrich:
                from .robot_strategies import features
                r['robot_features']=features(df,bench)
            out.append(r)
        except (ValueError,KeyError,TypeError,IndexError):continue
    return out

def latest_quote(code,now):
    from .market_data import yahoo_rows
    rows=yahoo_rows(code,period='1mo',interval='15m')['candles']
    for r in reversed(rows):
        start=datetime.fromtimestamp(r['time'],TR);end=datetime.fromtimestamp(r['time']+900,TR)
        if end<=now:
            return {**r,'start':start.isoformat(),'at':end.isoformat()}
    return None

def _directory():
    from .broker_bridge import _dir
    p=Path(os.getenv('BIST_AUTO_PAPER_DIR') or _dir()/'auto-paper');p.mkdir(parents=True,exist_ok=True);return p
def _key(token):
    if not re.fullmatch(r'[A-Za-z0-9_-]{40,100}',token or ''):raise ValueError('Otomatik hesap anahtarı geçersiz.')
    return hashlib.sha256(token.encode()).hexdigest()
def _read(key):return json.loads((_directory()/(key+'.json')).read_text())
def _write(key,a):
    path=_directory()/(key+'.json');tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(a,ensure_ascii=False,allow_nan=False));os.chmod(tmp,0o600);os.replace(tmp,path)
def create_account():
    token=secrets.token_urlsafe(32)
    with _LOCK:_write(_key(token),fresh())
    return {'token':token,'mode':'PAPER'}
def snapshot(token):
    with _LOCK:a=_read(_key(token))
    a['scan']['total']=len(a['scan']['codes'])
    a.pop('signal_keys',None);a['scan'].pop('rows',None);a['scan'].pop('codes',None)
    return {**a,'valuation':valuation(a),'mode':'PAPER','live_execution':False,'worker_running':bool(_THREAD and _THREAD.is_alive() and _RISK_THREAD and _RISK_THREAD.is_alive())}
def configure(token,payload):
    with _LOCK:
        key=_key(token);a=_read(key)
        for k,v in payload.items():
            if k not in DEFAULTS:raise ValueError('Bilinmeyen ayar: '+k)
            if k=='allow_short':
                if not isinstance(v,bool):raise ValueError('Açığa satış seçimi geçersiz.')
            else:
                limits={'max_positions':(1,10),'position_pct':(1,12),'gross_pct':(10,80),'risk_pct':(.1,1),'daily_loss_pct':(.5,5),'drawdown_pct':(2,20),'fee_bps':(0,100),'slippage_bps':(1,100),'borrow_annual_pct':(0,100),'min_coverage_pct':(50,100)}
                lo,hi=limits[k]
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi or (k=='max_positions' and int(v)!=v):raise ValueError('Ayar izin verilen aralığın dışında: '+k)
            a['config'][k]=v
        # Changing policy cancels queued entries. Exits remain active.
        a['pending']={c:o for c,o in a['pending'].items() if o['side'] in {'SELL','COVER'}}
        _write(key,a)
    return snapshot(token)
def control(token,action):
    with _LOCK:
        key=_key(token);a=_read(key)
        if action=='start':a['enabled']=True;a['scan'].update({'next_due':0,'retry_at':0})
        elif action in {'pause','close_all'}:
            a['enabled']=False;a['pending']={c:o for c,o in a['pending'].items() if o['side'] in {'SELL','COVER'}}
            if action=='close_all':
                for c,p in a['positions'].items():queue(a,c,'SELL' if p['quantity']>0 else 'COVER','Kullanıcı tümünü kapat ve durdur talebi.',now_tr())
        elif action=='refresh':a['last_cycle']=None;a['last_risk_check']=None;a['scan'].update({'next_due':0,'retry_at':0})
        else:raise ValueError('Geçersiz kontrol.')
        event(a,'CONTROL','',action);_write(key,a)
    start_worker();return snapshot(token)

def cycle(key,now=None,lane='combined'):
    if lane not in {'combined','scan','risk'}:raise ValueError('Geçersiz motor hattı')
    fixed_clock=now is not None;now=now or now_tr();request_start=now.isoformat();busy=(key,lane)
    with _LOCK:
        if busy in _BUSY:return
        a=_read(key);_BUSY.add(busy)
    try:
        # Quote control and full-universe downloads use independent workers.
        quotes={}
        if lane!='scan':
            codes=list(set(a['positions'])|set(a['pending']))
            def fetch(c):
                try:return c,latest_quote(c,now)
                except Exception:return c,None
            with ThreadPoolExecutor(max_workers=3) as ex:quotes=dict(ex.map(fetch,codes))
        batch=[];signals=[];universe=[];data_error=None;offset=0;epoch=None
        if lane!='risk' and a['enabled']:
            try:
                from .universe import get_universe
                from .market_data import daily_epoch
                u=get_universe()
                if not u or any(r.get('source')!='KAP' for r in u):raise ValueError('KAP evrenine ulaşılamadı; küçük yedek listeyle otomatik giriş yapılmaz.')
                universe=[r['ticker'] for r in u];epoch=daily_epoch(now)
                scan=a['scan'];offset=scan['cursor'] if scan['codes']==universe and scan.get('epoch')==epoch else 0
                batch=universe[offset:offset+20]
                signals=closed_signals(batch,now) if batch else []
            except Exception as e:data_error=str(e)[:250];batch=[]
        # Decision time is AFTER retrieval, never the earlier request start time.
        if not fixed_clock:now=now_tr()
        with _LOCK:
            # Every lane merges into the latest ledger; a pause/config change wins.
            a=_read(key)
            if lane!='scan':
                risk_check(a,now)
                for c,q in quotes.items():
                    if q:process_quote(a,c,q,now);risk_check(a,now)
                v=risk_check(a,now);a['curve'].append({'time':now.isoformat(),'equity':v['equity']});a['curve']=a['curve'][-2000:]
                a['last_risk_check']=now.isoformat()
            if lane!='risk':
                scan=a['scan']
                if a['enabled'] and batch:
                    if scan['codes']!=universe or scan.get('epoch')!=epoch:
                        scan.update({'codes':universe,'cursor':0,'rows':{},'epoch':epoch})
                    # Only this lane advances the cursor; stale/misaligned work is discarded.
                    if scan['cursor']==offset:
                        if not offset:scan['started_at']=request_start
                        scan['rows'].update({r['ticker']:r for r in signals});scan['cursor']+=len(batch)
                        scan['last_batch_at']=now.isoformat();scan['next_due']=0;scan['retry_at']=0
                        if scan['cursor']>=len(universe):
                            values=list(scan['rows'].values());latest=max((r['as_of'] for r in values),default='')
                            choose(a,[r for r in values if r['as_of']==latest],len(universe),now)
                            scan.update({'cursor':0,'rows':{},'completed_at':now.isoformat(),'completed_count':len(universe),'next_due':now.timestamp()+600})
                            scan['duration_sec']=round((now-datetime.fromisoformat(scan['started_at'])).total_seconds(),1)
                elif data_error:scan['retry_at']=now.timestamp()+30
                a['error']=data_error
            a['last_cycle']=now.isoformat();_write(key,a)
    except Exception as e:
        with _LOCK:
            a=_read(key);a['error']=str(e)[:250];a['last_cycle']=now.isoformat()
            if lane!='risk':a['scan']['retry_at']=now.timestamp()+30
            _write(key,a)
    finally:
        with _LOCK:_BUSY.discard(busy)

def scan_due(a,now):
    from .market_data import daily_epoch
    return a['enabled'] and now.timestamp()>=a['scan'].get('retry_at',0) and (a['scan'].get('epoch')!=daily_epoch(now) or now.timestamp()>=a['scan'].get('next_due',0))

def _loop(lane='scan'):
    while True:
        try:
            for path in list(_directory().glob('*.json')):
                try:
                    with _LOCK:a=_read(path.stem)
                    now=now_tr()
                    if lane=='scan':
                        if not scan_due(a,now):continue
                    else:
                        if not(a['enabled'] or a['positions'] or a['pending']):continue
                        last=a.get('last_risk_check')
                        if last and now.timestamp()-datetime.fromisoformat(last).timestamp()<30:continue
                    cycle(path.stem,lane=lane)
                except Exception:continue
        except Exception:pass
        time.sleep(1)

def start_worker():
    global _THREAD,_RISK_THREAD
    with _LOCK:
        if not(_THREAD and _THREAD.is_alive()):
            _THREAD=threading.Thread(target=_loop,args=('scan',),name='AutoPaperScan',daemon=True);_THREAD.start()
        if not(_RISK_THREAD and _RISK_THREAD.is_alive()):
            _RISK_THREAD=threading.Thread(target=_loop,args=('risk',),name='AutoPaperRisk',daemon=True);_RISK_THREAD.start()

def demo():
    """Deterministic synthetic fixture, kept completely outside forward account history."""
    from datetime import timedelta
    now=datetime(2026,10,23,11,0,tzinfo=TR);a=fresh();a['enabled']=True
    base={'signal_guard':{'status':'CLEAR'},'bar_provisional':False,'history_bars':250,'adx':30,'atr':2.,'price':100.,'avg_value_turnover_20':50_000_000.,'risk':40,'as_of':'2026-10-22'}
    rows=[{'ticker':'DEMOAL',**base,'short_score':82,'long_score':78,'supertrend':'BULLISH','macd_hist':1.,'rsi':55.},{'ticker':'DEMOSH',**base,'short_score':20,'long_score':25,'supertrend':'BEARISH','macd_hist':-1.,'rsi':40.}]
    choose(a,rows,2,now)
    for c in ['DEMOAL','DEMOSH']:
        q={'open':100.,'high':101.,'low':99.,'close':100.,'volume':1_000_000,'start':now.isoformat(),'at':(now+timedelta(minutes=15)).isoformat()}
        process_quote(a,c,q,now+timedelta(minutes=16))
    for c in ['DEMOAL','DEMOSH']:
        q={'open':100.,'high':110. if c=='DEMOAL' else 101.,'low':98. if c=='DEMOAL' else 90.,'close':109. if c=='DEMOAL' else 91.,'volume':1_000_000,'start':(now+timedelta(minutes=15)).isoformat(),'at':(now+timedelta(minutes=30)).isoformat()}
        process_quote(a,c,q,now+timedelta(minutes=31))
    for o in a['orders']:o.update({'mode':'SYNTHETIC_DEMO','source':'SYNTHETIC'})
    return {'mode':'SYNTHETIC_DEMO','note':'Üretilmiş iki fiyat senaryosu; gerçek hisse, geçmiş test veya ileri test performansı değildir. Otomatik hesabınızı değiştirmez.','orders':a['orders'],'decisions':a['decisions'],'valuation':valuation(a)}
