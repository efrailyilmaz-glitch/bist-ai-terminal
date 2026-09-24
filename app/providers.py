from __future__ import annotations
import os,time
from .universe import get_universe
from .market_data import yahoo_rows
from .news_engine import headlines

def provider_registry():
    return {
      'market':{'active':'YAHOO','licensed_ready':bool(os.getenv('MARKET_DATA_API_URL')),'env':'MARKET_DATA_API_URL'},
      'kap':{'active':'KAP_PUBLIC','licensed_ready':bool(os.getenv('KAP_API_URL')),'env':'KAP_API_URL'},
      'news':{'active':'GOOGLE_NEWS_RSS','licensed_ready':bool(os.getenv('NEWS_API_URL')),'env':'NEWS_API_URL'},
      'broker':{'active':'DISABLED','licensed_ready':bool(os.getenv('BROKER_API_URL')),'env':'BROKER_API_URL'}
    }

def _check(name,fn):
    t=time.perf_counter()
    try:
        detail=fn()
        return {'name':name,'status':'OK','latency_ms':round((time.perf_counter()-t)*1000),'detail':detail}
    except Exception as e:
        return {'name':name,'status':'ERROR','latency_ms':round((time.perf_counter()-t)*1000),'error':str(e)[:160]}

def data_health():
    checks=[]
    checks.append(_check('KAP Universe',lambda:{'count':len(get_universe()),'source':(get_universe()[0].get('source') if get_universe() else 'NONE')}))
    checks.append(_check('Yahoo XU100',lambda:{'candles':len(yahoo_rows('XU100','1mo','1d').get('candles',[]))}))
    checks.append(_check('Google News RSS',lambda:{'status':headlines('ASELS',3).get('status')}))
    ok=sum(1 for x in checks if x['status']=='OK')
    return {'status':'HEALTHY' if ok==len(checks) else ('DEGRADED' if ok else 'DOWN'),
            'ok':ok,'total':len(checks),'providers':provider_registry(),'checks':checks,'timestamp':time.strftime('%d.%m.%Y %H:%M:%S')}
