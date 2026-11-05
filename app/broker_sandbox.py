"""V125 broker-integration sandbox.
Uses the existing paper/risk bridge only. No adapter in this module can submit a live broker order.
"""
from __future__ import annotations
import hashlib,json,threading,time
from .runtime_paths import data_path
from .broker_bridge import broker_status,order_preview,paper_order

_LOCK=threading.Lock()
_FILE=data_path('broker_sandbox_idempotency.json')

def _canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str)

def _load():
    try:
        d=json.loads(_FILE.read_text(encoding='utf-8'))
        return d if isinstance(d,dict) else {}
    except Exception:return {}

def _save(d):
    tmp=_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(_FILE)

def status():
    b=broker_status()
    return {'status':'OK','version':'125.0','mode':'SANDBOX_ONLY',
            'direct_live_execution_enabled':False,
            'official_api_configured':bool(b.get('direct_official_api_configured')),
            'kill_switch':bool(b.get('kill_switch')),'risk':b.get('risk') or {},
            'controls':['kill_switch','max_order_value','max_position_pct','max_positions',
                        'max_daily_loss_pct','idempotency_key','paper_position_check'],
            'adapters':[
              {'id':'internal_paper','status':'CONNECTED','submit_mode':'PAPER_ONLY'},
              {'id':'info_official','status':'LIVE_LOCKED','submit_mode':'NO_LIVE_IMPLEMENTATION',
               'configured':bool(b.get('direct_official_api_configured'))}
            ],
            'policy':'Broker sandbox can preview and record paper fills only. No live-order submission method exists here.'}

def preview(payload):
    p=order_preview(payload or {})
    return {'status':'BLOCKED' if p.get('blocked') else 'READY_FOR_SANDBOX',
            'mode':'SANDBOX_ONLY','direct_live_execution_enabled':False,'preview':p}

def submit(payload,idempotency_key):
    key=str(idempotency_key or '').strip()
    if len(key)<8 or len(key)>128:
        return {'status':'BLOCKED','reason':'IDEMPOTENCY_KEY_REQUIRED_8_TO_128_CHARS',
                'direct_live_execution_enabled':False}
    body=dict(payload or {})
    digest=hashlib.sha256(_canon(body).encode()).hexdigest()
    with _LOCK:
        ledger=_load();old=ledger.get(key)
        if old:
            if old.get('payload_hash')!=digest:
                return {'status':'BLOCKED','reason':'IDEMPOTENCY_KEY_PAYLOAD_CONFLICT',
                        'direct_live_execution_enabled':False}
            if old.get('state')=='RESERVED':
                return {'status':'DUPLICATE_PENDING','idempotency_key':key,
                        'reason':'PRIOR_SANDBOX_SUBMISSION_RESERVED_REVIEW_REQUIRED',
                        'direct_live_execution_enabled':False}
            return {'status':'DUPLICATE_REPLAY','idempotency_key':key,'result':old.get('result'),
                    'direct_live_execution_enabled':False}
        pre=order_preview(body)
        ledger[key]={'payload_hash':digest,'created_epoch':time.time(),'state':'RESERVED','result':None}
        _save(ledger)
        if pre.get('blocked'):
            result={'status':'BLOCKED','preview':pre}
        else:
            result=paper_order(body)
        ledger=_load()
        ledger[key]={'payload_hash':digest,'created_epoch':ledger.get(key,{}).get('created_epoch',time.time()),
                     'state':'FINAL','result':result}
        if len(ledger)>2000:
            keep=sorted(ledger.items(),key=lambda kv:float(kv[1].get('created_epoch') or 0),reverse=True)[:1500]
            ledger=dict(keep)
        _save(ledger)
    return {'status':'OK' if result.get('status')=='OK' else result.get('status','BLOCKED'),
            'idempotency_key':key,'result':result,'direct_live_execution_enabled':False}
