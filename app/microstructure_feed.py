"""Licensed Level-2/order-event adapter.
No vendor contract is assumed. Configure LEVEL2_API_URL as either a URL template
containing {ticker}, or an endpoint accepting ?ticker=. Optional LEVEL2_API_TOKEN
is sent as Bearer auth. Malformed/stale data never becomes positive evidence.
"""
from __future__ import annotations
import os,time,requests
from datetime import datetime,timezone
from .microstructure import microstructure_guard

_CACHE={}

def _url(code):
    base=(os.getenv('LEVEL2_API_URL') or '').strip()
    if not base:return None
    return base.format(ticker=code) if '{ticker}' in base else base

def _age_seconds(ts):
    if ts is None:return None
    try:
        if isinstance(ts,(int,float)):return max(0,time.time()-float(ts))
        dt=datetime.fromisoformat(str(ts).replace('Z','+00:00'))
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        return max(0,(datetime.now(timezone.utc)-dt.astimezone(timezone.utc)).total_seconds())
    except Exception:return None

def latest_microstructure(ticker,max_age_seconds=30):
    code=str(ticker).upper().replace('.IS','');url=_url(code)
    if not url:
        return {'configured':False,'ticker':code,'status':'UNKNOWN','guard':microstructure_guard(None),'source':'NONE'}
    now=time.time();hit=_CACHE.get(code)
    if hit and now-hit[0]<2:return hit[1]
    headers={'Accept':'application/json','User-Agent':'BIST-AI-Terminal/38.0'}
    token=(os.getenv('LEVEL2_API_TOKEN') or '').strip()
    if token:headers['Authorization']='Bearer '+token
    try:
        params=None if '{ticker}' in (os.getenv('LEVEL2_API_URL') or '') else {'ticker':code}
        r=requests.get(url,params=params,headers=headers,timeout=2.5);r.raise_for_status();obj=r.json()
        if isinstance(obj,dict) and isinstance(obj.get('data'),dict):obj=obj['data']
        if not isinstance(obj,dict):raise ValueError('invalid_level2_payload')
        age=_age_seconds(obj.get('timestamp') or obj.get('as_of') or obj.get('time'))
        guard=microstructure_guard(obj)
        flags=list(guard.get('flags') or [])
        if age is None:
            flags.append('TIMESTAMP_MISSING');guard={**guard,'status':'CAUTION','risk_multiplier':min(.75,float(guard.get('risk_multiplier',1))), 'flags':flags}
        elif age>max_age_seconds:
            flags.append('LEVEL2_STALE');guard={**guard,'status':'CAUTION','risk_multiplier':min(.65,float(guard.get('risk_multiplier',1))), 'flags':flags}
        out={'configured':True,'ticker':code,'status':'OK','age_seconds':None if age is None else round(age,2),
             'guard':guard,'source':'LICENSED_LEVEL2_ADAPTER'}
    except Exception as e:
        out={'configured':True,'ticker':code,'status':'ERROR','guard':{'status':'CAUTION','score':0,'flags':['LEVEL2_FETCH_ERROR'],'risk_multiplier':.75},
             'source':'LICENSED_LEVEL2_ADAPTER','error':str(e)[:160]}
    _CACHE[code]=(now,out);return out
