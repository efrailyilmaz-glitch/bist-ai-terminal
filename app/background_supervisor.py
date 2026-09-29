from __future__ import annotations
import threading,time
from .opportunity_engine import trigger_refresh, radar_snapshot
from .pro_alert_engine import evaluate_once, list_rules
_THREAD=None
_STATE={'running':False,'last_fast_check':None,'last_heavy_refresh':None,'cycles':0,'error':None}
def _loop():
    _STATE['running']=True
    last_heavy=0
    while True:
        try:
            now=time.time()
            evaluate_once();_STATE['last_fast_check']=time.strftime('%d.%m.%Y %H:%M:%S')
            if now-last_heavy>=15*60:
                trigger_refresh();last_heavy=now;_STATE['last_heavy_refresh']=time.strftime('%d.%m.%Y %H:%M:%S')
            _STATE['cycles']+=1;_STATE['error']=None
        except Exception as e:_STATE['error']=str(e)[:300]
        time.sleep(60)
def start_background_supervisor():
    global _THREAD
    if _THREAD and _THREAD.is_alive():return
    _THREAD=threading.Thread(target=_loop,name='BISTAlwaysOnSupervisor',daemon=True);_THREAD.start()
def status():
    r=radar_snapshot(limit=5);a=list_rules()
    return {**_STATE,'radar_status':r.get('status'),'radar_last_scan':r.get('last_scan'),'opportunity_count':len(r.get('opportunities') or []),
            'pro_alert_rules':len(a.get('rules') or []),'cadence':{'fast_alert_seconds':60,'heavy_radar_minutes':15},
            'note':'Runs continuously while the BIST AI backend is alive. A sleeping/off computer cannot run local scans.'}
