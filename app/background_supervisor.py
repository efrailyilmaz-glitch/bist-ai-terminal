from __future__ import annotations
import threading,time
from datetime import datetime
from zoneinfo import ZoneInfo
from .opportunity_engine import trigger_refresh, radar_snapshot, smart_money_candidates
from .pro_alert_engine import evaluate_once, list_rules
from .investment_committee import investment_committee
from .experience_engine import record_signal, settle_due
from .smart_money_engine import smart_money_snapshot

_THREAD=None
_STATE={'running':False,'last_fast_check':None,'last_heavy_refresh':None,'last_committee_run':None,'last_settlement':None,'cycles':0,'error':None,'market_phase':'UNKNOWN','committee_reviews':[],'alerts':[]}
_LAST_RADAR_SCAN=None;_LAST_COMMITTEE={};_LAST_SM_ALERT={}

def _now_tr():return datetime.now(ZoneInfo('Europe/Istanbul'))
def market_phase(dt=None):
    dt=dt or _now_tr()
    if dt.weekday()>=5:return 'CLOSED_WEEKEND'
    m=dt.hour*60+dt.minute
    if m<570:return 'PRE_MARKET'
    if m<600:return 'OPENING'
    if m<=1080:return 'CONTINUOUS'
    if m<=1090:return 'CLOSING'
    return 'CLOSED'
def _cadence(phase):
    if phase in {'OPENING','CONTINUOUS','CLOSING'}:return 60,15*60
    if phase=='PRE_MARKET':return 180,30*60
    return 300,60*60
def _review_top():
    global _LAST_RADAR_SCAN
    snap=radar_snapshot(limit=12);scan=snap.get('last_scan')
    if not scan or scan==_LAST_RADAR_SCAN:return
    _LAST_RADAR_SCAN=scan
    candidates=[x for x in (snap.get('opportunities') or []) if x.get('grade') in {'MEGA','STRONG'}][:3]
    reviews=[]
    for s in candidates:
        code=s.get('ticker');now=time.time()
        if now-_LAST_COMMITTEE.get(code,0)<6*3600:
            record_signal(s,None);continue
        try:
            c=investment_committee(code);_LAST_COMMITTEE[code]=now
            rid=record_signal(s,c)
            item={'ticker':code,'decision':c.get('decision'),'decision_tr':c.get('decision_tr'),'committee_score':c.get('committee_score'),
                  'opportunity_score':s.get('opportunity_score'),'record_id':rid,'time':time.strftime('%d.%m.%Y %H:%M:%S')}
            reviews.append(item)
            if c.get('decision')=='PASS':
                evt={'id':int(time.time()*1000),'type':'COMMITTEE_PASS','ticker':code,'score':c.get('committee_score'),'opportunity_score':s.get('opportunity_score'),
                     'message':f"{code} · Komite {c.get('committee_score')}/100 · Fırsat {s.get('opportunity_score')}/100",'created_at':item['time']}
                _STATE['alerts'].insert(0,evt);_STATE['alerts']=_STATE['alerts'][:200]
        except Exception as e:
            reviews.append({'ticker':code,'decision':'ERROR','error':str(e)[:120],'time':time.strftime('%d.%m.%Y %H:%M:%S')})
    # Smart-money deep check is independent from opportunity rank: pre-markup often appears before classic momentum.
    sm_candidates=(smart_money_candidates(limit=16).get('rows') or [])
    for s in sm_candidates:
        code=s.get('ticker')
        try:
            sm=smart_money_snapshot(code,calibrate=False)
            typ=None
            if sm.get('phase')=='PRE_MARKUP_WATCH' and sm.get('accumulation_probability',0)>=78 and sm.get('markup_probability',0)>=72:
                typ='PRE_MARKUP_WATCH'
            elif sm.get('distribution_risk',0)>=82:
                typ='DISTRIBUTION_RISK'
            if not typ: continue
            key=f"{code}:{typ}";now=time.time()
            if now-_LAST_SM_ALERT.get(key,0)<6*3600: continue
            _LAST_SM_ALERT[key]=now
            if typ=='PRE_MARKUP_WATCH':
                evt={'id':int(now*1000)+len(_STATE['alerts']),'type':typ,'ticker':code,'score':sm.get('accumulation_probability'),
                     'message':f"{code} · Birikim {sm.get('accumulation_probability')} · Markup {sm.get('markup_probability')}",'created_at':time.strftime('%d.%m.%Y %H:%M:%S')}
            else:
                evt={'id':int(now*1000)+len(_STATE['alerts']),'type':typ,'ticker':code,'score':sm.get('distribution_risk'),
                     'message':f"{code} · Dağıtım riski {sm.get('distribution_risk')} · Exit {sm.get('exit_risk')}",'created_at':time.strftime('%d.%m.%Y %H:%M:%S')}
            _STATE['alerts'].insert(0,evt);_STATE['alerts']=_STATE['alerts'][:200]
        except Exception:pass
    if reviews:
        _STATE['committee_reviews']=(reviews+_STATE['committee_reviews'])[:50]
        _STATE['last_committee_run']=time.strftime('%d.%m.%Y %H:%M:%S')
def _loop():
    _STATE['running']=True;last_heavy=0;last_settle=0
    while True:
        try:
            now=time.time();phase=market_phase();_STATE['market_phase']=phase
            fast,heavy=_cadence(phase)
            evaluate_once();_STATE['last_fast_check']=time.strftime('%d.%m.%Y %H:%M:%S')
            if now-last_heavy>=heavy:
                trigger_refresh();last_heavy=now;_STATE['last_heavy_refresh']=time.strftime('%d.%m.%Y %H:%M:%S')
            _review_top()
            if now-last_settle>=6*3600:
                settle_due();last_settle=now;_STATE['last_settlement']=time.strftime('%d.%m.%Y %H:%M:%S')
            _STATE['cycles']+=1;_STATE['error']=None
        except Exception as e:_STATE['error']=str(e)[:300]
        time.sleep(_cadence(_STATE['market_phase'])[0])
def start_background_supervisor():
    global _THREAD
    if _THREAD and _THREAD.is_alive():return
    _THREAD=threading.Thread(target=_loop,name='BISTAlwaysOnSupervisor',daemon=True);_THREAD.start()
def status():
    r=radar_snapshot(limit=5);a=list_rules();fast,heavy=_cadence(_STATE.get('market_phase','CLOSED'))
    return {**_STATE,'radar_status':r.get('status'),'radar_last_scan':r.get('last_scan'),'opportunity_count':len(r.get('opportunities') or []),
            'pro_alert_rules':len(a.get('rules') or []),'cadence':{'fast_seconds':fast,'heavy_minutes':round(heavy/60)},
            'note':'Market-hours-aware continuous supervisor. Runs while the backend is alive; sleeping/off computer requires a server deployment.'}
def alerts(limit=50,since=0):
    return {'alerts':[x for x in _STATE['alerts'] if int(x.get('id',0))>int(since or 0)][:max(1,min(int(limit),100))]}
