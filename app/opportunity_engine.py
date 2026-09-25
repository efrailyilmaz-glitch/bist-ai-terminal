from __future__ import annotations
import json, math, os, platform, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from .market_data import scan_codes, market_overview
from .universe import get_universe
from .fundamentals import get_fundamentals
from .kap_engine import disclosures
from .news_engine import headlines
from .analyst_engine import trusted_research

_LOCK=threading.Lock();_WAKE=threading.Event();_THREAD=None;INTERVAL=15*60
_STATE={'status':'IDLE','running':False,'last_scan':None,'duration_sec':None,'universe_count':0,'analyzed_count':0,'opportunities':[],'alerts':[],'error':None}
def _v(x,d=50.0):
    try:
        v=float(x);return d if math.isnan(v) or math.isinf(v) else v
    except Exception:return float(d)
def _cap(x,a=0,b=100):return max(a,min(b,x))
def _kap(k):
    items=(k or {}).get('items') or []
    if not items:return 50
    z=[(50+_v(x.get('sentiment_score'),0)/2,max(10,_v(x.get('materiality'),25))) for x in items];den=sum(w for _,w in z)
    return _cap(sum(s*w for s,w in z)/den if den else 50)
def _news(n):
    s=(n or {}).get('headline_sentiment');return 50 if s is None else _cap(50+_v(s,0)/2)
def _targets(t,a=None,f=None):
    p=_v(t.get('price'),0);atr=max(_v(t.get('atr'),p*.025),p*.005 if p else .01)
    if p<=0:return {}
    res=sorted([_v(x,0) for x in (t.get('resistances') or []) if _v(x,0)>p]);sup=sorted([_v(x,0) for x in (t.get('supports') or []) if 0<_v(x,0)<p],reverse=True)
    t1=res[0] if res and res[0]<=p+2.6*atr else p+1.8*atr;t2=res[1] if len(res)>1 and res[1]<=p+5*atr else max(t1,p+3.4*atr)
    stop=sup[0] if sup and sup[0]>=p-2.2*atr else p-1.45*atr;medium=p+4.8*atr
    cons=_v((a or {}).get('consensus_target'),0);yt=_v((f or {}).get('target_mean_price'),0);lc=[x for x in [cons,yt] if x>p*.70]
    if lc:long=round(sum(lc)/len(lc),2);method='Analist konsensüsü / kamuya açık hedefler'
    else:
        mom=max(-10,min(30,_v(t.get('momentum_120'),0)*.35+_v(t.get('relative_strength_60'),0)*.20));long=round(max(p+6.5*atr,p*(1+max(8,mom)/100)),2);method='Teknik senaryo (ATR + uzun momentum)'
    lstop=sup[-1] if sup and sup[-1]>=p-5*atr else max(0,p-4*atr)
    return {'short_target_1':round(t1,2),'short_target_2':round(t2,2),'short_stop':round(max(0,stop),2),'short_horizon':'2–20 işlem günü',
            'medium_target':round(medium,2),'medium_horizon':'1–3 ay','long_target':long,'long_stop_reference':round(max(0,lstop),2),'long_horizon':'6–12 ay',
            'long_target_method':method,'analyst_consensus_target':round(cons,2) if cons else None}
def score_opportunity(t,fundamentals=None,analyst=None,macro=None,kap=None,news=None):
    f=fundamentals or {};a=analyst or {};m=macro or {};k=kap or {};n=news or {}
    s=_v(t.get('short_score'));l=_v(t.get('long_score'));smart=_v(t.get('smart_money_score'));fund=_v(f.get('fundamental_score'));ana=_v(a.get('analyst_score'))
    ks=_kap(k);ns=_news(n);ms=_v(m.get('global_score'));rs=_v(t.get('relative_strength_20'),0);vr=_v(t.get('volume_ratio'),1);risk=_v(t.get('risk'));anom=_v(t.get('anomaly_score'),0);liq=_v(t.get('avg_value_turnover_20'),0)
    base=.28*s+.16*l+.14*fund+.12*ana+.08*ks+.05*ns+.07*ms+.10*smart;bonus=0;conf=[]
    if t.get('breakout20') and vr>=1.3:bonus+=6;conf.append('Breakout + hacim')
    if t.get('supertrend')=='BULLISH':bonus+=3;conf.append('Supertrend bullish')
    if t.get('ichimoku')=='BULLISH':bonus+=3;conf.append('Ichimoku bullish')
    if rs>=5:bonus+=4;conf.append('XU100 relative strength')
    if _v(t.get('adx'),0)>=25 and _v(t.get('plus_di'),0)>_v(t.get('minus_di'),0):bonus+=3;conf.append('ADX trend teyidi')
    if t.get('rsi_divergence')=='BULLISH' or t.get('macd_divergence')=='BULLISH':bonus+=3;conf.append('Bullish divergence')
    if f.get('quality_score') is not None and _v(f.get('quality_score'))>=70:bonus+=3;conf.append('Kalite faktörü güçlü')
    if f.get('growth_score') is not None and _v(f.get('growth_score'))>=70:bonus+=2;conf.append('Büyüme faktörü güçlü')
    if a.get('consensus_upside_pct') is not None and _v(a.get('consensus_upside_pct'),0)>=20:bonus+=3;conf.append('Analist hedef desteği')
    if ks>=62:bonus+=3;conf.append('Pozitif KAP katalizörü')
    penalty=max(0,risk-60)*.18+max(0,anom-75)*.12;warn=[]
    if liq and liq<5_000_000:penalty+=8;warn.append('Düşük likidite')
    if risk>=75:warn.append('Yüksek volatilite riski')
    if anom>=80:warn.append('Aşırı fiyat/hacim anomalisi')
    if t.get('supertrend')=='BEARISH' and t.get('ichimoku')=='BEARISH':penalty+=7;warn.append('Trend yapısı negatif')
    overall=int(round(_cap(base+bonus-penalty)));short=int(round(_cap(.58*s+.12*smart+.10*ms+.08*ks+.06*ns+.06*ana+bonus*.6-penalty)));long=int(round(_cap(.28*l+.28*fund+.20*ana+.08*ks+.06*ns+.10*ms+bonus*.45-penalty*.65)))
    grade='MEGA' if overall>=86 and len(conf)>=5 and risk<72 else 'STRONG' if overall>=78 and len(conf)>=4 else 'WATCH' if overall>=66 else 'NORMAL'
    return {'ticker':t.get('ticker'),'price':t.get('price'),'opportunity_score':overall,'short_opportunity_score':short,'long_opportunity_score':long,'grade':grade,
            'label':'BÜYÜK FIRSAT ADAYI' if grade=='MEGA' else 'GÜÇLÜ FIRSAT' if grade=='STRONG' else 'İZLE' if grade=='WATCH' else 'NORMAL',
            'confidence':int(round(_cap(len(conf)*12+min(35,(a.get('coverage_count') or 0)*10)+min(25,_v(f.get('coverage_pct'),0)*.25)))),
            'confirmations':conf[:8],'warnings':warn[:6],'targets':_targets(t,a,f),'components':{'technical_short':round(s),'technical_long':round(l),'fundamental':round(fund),'analyst':round(ana),'kap':round(ks),'news':round(ns),'macro':round(ms),'smart_money':round(smart),'risk':round(risk),'anomaly':round(anom)},'avg_value_turnover_20':liq,'updated':time.strftime('%d.%m.%Y %H:%M:%S')}
def _file():
    if platform.system()=='Darwin':b=Path.home()/'Library'/'Application Support'/'BIST AI Terminal'
    elif platform.system()=='Windows':b=Path(os.getenv('APPDATA') or Path.home())/'BIST AI Terminal'
    else:b=Path.home()/'.bist-ai-terminal'
    try:b.mkdir(parents=True,exist_ok=True)
    except Exception:pass
    return b/'opportunity_state.json'
def _save():
    try:
        with _LOCK:d={'last_scan':_STATE['last_scan'],'opportunities':_STATE['opportunities'][:60],'alerts':_STATE['alerts'][:250]}
        _file().write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
    except Exception:pass
def _load():
    try:
        p=_file()
        if not p.exists():return
        d=json.loads(p.read_text(encoding='utf-8'))
        with _LOCK:_STATE['last_scan']=d.get('last_scan');_STATE['opportunities']=d.get('opportunities') or [];_STATE['alerts']=d.get('alerts') or []
    except Exception:pass
def _alert(o):return {'id':int(time.time()*1000),'ticker':o.get('ticker'),'grade':o.get('grade'),'label':o.get('label'),'score':o.get('opportunity_score'),'short_score':o.get('short_opportunity_score'),'long_score':o.get('long_opportunity_score'),'price':o.get('price'),'targets':o.get('targets'),'confirmations':o.get('confirmations'),'created_at':time.strftime('%d.%m.%Y %H:%M:%S')}
def run_radar_once():
    st=time.time()
    with _LOCK:_STATE.update({'status':'SCANNING','running':True,'error':None})
    try:
        u=get_universe();codes=[x['ticker'] for x in u];macro=market_overview();rows=scan_codes(codes);basic=[score_opportunity(r,macro=macro) for r in rows];basic.sort(key=lambda x:x['opportunity_score'],reverse=True);top=[x['ticker'] for x in basic[:18] if x.get('ticker')];tm={r['ticker']:r for r in rows};rich=[]
        def enrich(code):
            t=tm[code];f=get_fundamentals(code);a=trusted_research(code,current_price=_v(t.get('price'),0),fundamentals=f);idx=top.index(code);k=disclosures(code,8) if idx<8 else {};n=headlines(code,10) if idx<8 else {};o=score_opportunity(t,f,a,macro,k,n);o['analyst']=a;o['fundamental_score']=f.get('fundamental_score');return o
        with ThreadPoolExecutor(max_workers=4) as ex:
            fs=[ex.submit(enrich,c) for c in top]
            for q in as_completed(fs):
                try:rich.append(q.result())
                except Exception:pass
        rich.sort(key=lambda x:x['opportunity_score'],reverse=True);ops=(rich+[x for x in basic if x.get('ticker') not in top])[:80]
        with _LOCK:
            old={x.get('ticker'):x for x in _STATE['opportunities']};alerts=list(_STATE['alerts'])
            for o in ops:
                if o.get('grade') not in {'MEGA','STRONG'}:continue
                p=old.get(o.get('ticker')) or {}
                if p.get('grade')==o.get('grade') and abs(_v(p.get('opportunity_score'),0)-_v(o.get('opportunity_score'),0))<5:continue
                alerts.insert(0,_alert(o))
            _STATE.update({'status':'OK','running':False,'last_scan':time.strftime('%d.%m.%Y %H:%M:%S'),'duration_sec':round(time.time()-st,1),'universe_count':len(codes),'analyzed_count':len(rows),'opportunities':ops,'alerts':alerts[:250]})
        _save()
    except Exception as e:
        with _LOCK:_STATE.update({'status':'ERROR','running':False,'duration_sec':round(time.time()-st,1),'error':str(e)[:250]})
def _loop():
    _load();_WAKE.wait(25);_WAKE.clear();run_radar_once()
    while True:_WAKE.wait(INTERVAL);_WAKE.clear();run_radar_once()
def start_radar():
    global _THREAD
    with _LOCK:
        if _THREAD and _THREAD.is_alive():return
        _STATE['status']='STARTING';_THREAD=threading.Thread(target=_loop,name='BISTOpportunityRadar',daemon=True);_THREAD.start()
def trigger_refresh():_WAKE.set();return {'queued':True,'status':_STATE.get('status')}
def radar_snapshot(limit=60):
    with _LOCK:return {'status':_STATE['status'],'running':_STATE['running'],'last_scan':_STATE['last_scan'],'duration_sec':_STATE['duration_sec'],'universe_count':_STATE['universe_count'],'analyzed_count':_STATE['analyzed_count'],'error':_STATE['error'],'opportunities':list(_STATE['opportunities'])[:max(1,min(limit,100))]}
def alerts_snapshot(limit=50,since=0):
    with _LOCK:return {'alerts':[x for x in _STATE['alerts'] if int(x.get('id',0))>int(since or 0)][:max(1,min(limit,100))],'last_scan':_STATE['last_scan'],'status':_STATE['status']}
