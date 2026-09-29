from __future__ import annotations
import json, os, platform, threading, time, uuid
from pathlib import Path
from .market_data import scan_codes
from .premium_engine import fair_value_health

_LOCK=threading.Lock();_THREAD=None;_WAKE=threading.Event();INTERVAL=300
_STATE={'rules':[],'events':[],'last_eval':None,'error':None}
OPS={'>':lambda a,b:a>b,'>=':lambda a,b:a>=b,'<':lambda a,b:a<b,'<=':lambda a,b:a<=b,'==':lambda a,b:a==b,'!=':lambda a,b:a!=b}
PREMIUM_FIELDS={'fair_value_upside_pct','health_score','piotroski_score','altman_score'}

def _file():
    if platform.system()=='Darwin':b=Path.home()/'Library'/'Application Support'/'BIST AI Terminal'
    elif platform.system()=='Windows':b=Path(os.getenv('APPDATA') or Path.home())/'BIST AI Terminal'
    else:b=Path.home()/'.bist-ai-terminal'
    b.mkdir(parents=True,exist_ok=True);return b/'pro_alerts.json'
def _save():
    try:
        with _LOCK:d={'rules':_STATE['rules'],'events':_STATE['events'][:500]}
        _file().write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
    except Exception:pass
def _load():
    try:
        p=_file()
        if p.exists():
            d=json.loads(p.read_text(encoding='utf-8'))
            with _LOCK:_STATE['rules']=d.get('rules') or [];_STATE['events']=d.get('events') or []
    except Exception:pass
def _num(x):
    try:return float(x)
    except Exception:return x
def _values(ticker,fields):
    tech=(scan_codes([ticker]) or [{}])[0];vals=dict(tech)
    if any(f in PREMIUM_FIELDS for f in fields):
        p=fair_value_health(ticker)
        vals['fair_value_upside_pct']=p.get('fair_value_upside_pct');vals['health_score']=p.get('health_score')
        vals['piotroski_score']=(p.get('piotroski') or {}).get('score');vals['altman_score']=(p.get('altman') or {}).get('score')
    return vals
def _condition(c,vals):
    field=c.get('field');op=c.get('op','>');target=c.get('value');actual=vals.get(field)
    if actual is None:return False
    if op=='between':
        lo=c.get('min');hi=c.get('max')
        try:return float(lo)<=float(actual)<=float(hi)
        except Exception:return False
    try:return OPS.get(op,OPS['>'])(float(actual),float(target))
    except Exception:return OPS.get(op,OPS['=='])(str(actual),str(target))
def add_rule(payload):
    rule={'id':uuid.uuid4().hex[:12],'name':payload.get('name') or 'Özel Alarm','ticker':str(payload.get('ticker','')).upper().replace('.IS',''),
          'mode':'any' if payload.get('mode')=='any' else 'all','conditions':payload.get('conditions') or [],'enabled':True,
          'cooldown_minutes':max(5,int(payload.get('cooldown_minutes',60))),'last_trigger':None,'created_at':time.strftime('%d.%m.%Y %H:%M:%S')}
    if not rule['ticker'] or not rule['conditions']:raise ValueError('ticker and conditions required')
    with _LOCK:_STATE['rules'].append(rule)
    _save();_WAKE.set();return rule
def delete_rule(rule_id):
    with _LOCK:
        before=len(_STATE['rules']);_STATE['rules']=[x for x in _STATE['rules'] if x.get('id')!=rule_id]
    _save();return {'deleted':before-len(_STATE['rules'])}
def list_rules():
    with _LOCK:return {'rules':list(_STATE['rules']),'last_eval':_STATE['last_eval'],'error':_STATE['error']}
def events(limit=100,since=0):
    with _LOCK:return {'events':[x for x in _STATE['events'] if int(x.get('id',0))>int(since or 0)][:max(1,min(limit,200))],'last_eval':_STATE['last_eval']}
def evaluate_once():
    try:
        with _LOCK:rules=[dict(x) for x in _STATE['rules'] if x.get('enabled')]
        by={}
        for r in rules:by.setdefault(r['ticker'],[]).append(r)
        now=time.time();new=[]
        for ticker,rr in by.items():
            fields={c.get('field') for r in rr for c in r.get('conditions',[])}
            vals=_values(ticker,fields)
            for r in rr:
                checks=[_condition(c,vals) for c in r.get('conditions',[])]
                ok=any(checks) if r.get('mode')=='any' else all(checks)
                last=r.get('last_trigger_epoch') or 0
                if ok and now-last>=r.get('cooldown_minutes',60)*60:
                    evt={'id':int(now*1000)+len(new),'rule_id':r['id'],'name':r['name'],'ticker':ticker,'conditions':r['conditions'],'values':{f:vals.get(f) for f in fields},'created_at':time.strftime('%d.%m.%Y %H:%M:%S')}
                    new.append(evt)
                    with _LOCK:
                        for real in _STATE['rules']:
                            if real.get('id')==r['id']:real['last_trigger']=evt['created_at'];real['last_trigger_epoch']=now
        with _LOCK:
            if new:_STATE['events']=new+_STATE['events']
            _STATE['last_eval']=time.strftime('%d.%m.%Y %H:%M:%S');_STATE['error']=None
        _save();return {'triggered':len(new),'events':new}
    except Exception as e:
        with _LOCK:_STATE['error']=str(e)[:240]
        return {'triggered':0,'error':str(e)}
def _loop():
    _load();time.sleep(20)
    while True:
        evaluate_once();_WAKE.wait(INTERVAL);_WAKE.clear()
def start_alert_engine():
    global _THREAD
    if _THREAD and _THREAD.is_alive():return
    _THREAD=threading.Thread(target=_loop,name='BISTProAlerts',daemon=True);_THREAD.start()
