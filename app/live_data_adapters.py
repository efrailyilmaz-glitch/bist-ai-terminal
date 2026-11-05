"""V124 live-market data adapter architecture.
Public delayed data is available through Yahoo. Licensed real-time/depth providers are explicit
adapter slots and remain NOT_CONFIGURED until a real provider implementation + credentials exist.
No order-book/depth data is synthesized.
"""
from __future__ import annotations
import os,time
from dataclasses import dataclass
from typing import Any
from .market_data import yahoo_rows

@dataclass(frozen=True)
class AdapterInfo:
    id:str
    name:str
    realtime:bool
    depth:bool
    requires_license:bool
    env_key:str|None=None

CATALOG=[
    AdapterInfo('yahoo_delayed','Yahoo Finance Delayed',False,False,False,None),
    AdapterInfo('matriks','Matriks',True,True,True,'MATRIKS_API_TOKEN'),
    AdapterInfo('is_yatirim','İş Yatırım',True,False,True,'IS_YATIRIM_API_TOKEN'),
    AdapterInfo('info_yatirim','Info Yatırım',True,False,True,'INFO_YATIRIM_API_TOKEN'),
]

class BaseAdapter:
    info:AdapterInfo
    def status(self)->dict[str,Any]:raise NotImplementedError
    def quote(self,ticker:str)->dict[str,Any]:raise NotImplementedError
    def candles(self,ticker:str,period='1mo',interval='1d')->dict[str,Any]:raise NotImplementedError
    def depth_snapshot(self,ticker:str)->dict[str,Any]:
        return {'status':'UNAVAILABLE','ticker':ticker.upper().replace('.IS',''),
                'provider':self.info.id,'reason':'DEPTH_NOT_SUPPORTED_OR_NOT_CONNECTED',
                'synthetic':False}

class YahooDelayedAdapter(BaseAdapter):
    info=CATALOG[0]
    def status(self):
        return {'id':self.info.id,'name':self.info.name,'status':'AVAILABLE_DELAYED',
                'realtime':False,'depth':False,'requires_license':False,
                'note':'Public delayed market-data fallback; not a real-time execution feed.'}
    def candles(self,ticker,period='1mo',interval='1d'):
        d=yahoo_rows(ticker,period=period,interval=interval)
        return {'status':'OK','provider':self.info.id,'realtime':False,'depth':False,
                'fetched_epoch':time.time(),**d}
    def quote(self,ticker):
        d=yahoo_rows(ticker,period='1mo',interval='1d');rows=d.get('candles') or []
        if not rows:return {'status':'NO_DATA','provider':self.info.id,'ticker':ticker}
        last=rows[-1]
        return {'status':'OK','provider':self.info.id,'ticker':d.get('ticker'),'realtime':False,
                'price':last.get('close'),'open':last.get('open'),'high':last.get('high'),'low':last.get('low'),
                'volume':last.get('volume'),'as_of':last.get('time'),'fetched_epoch':time.time(),
                'note':'Delayed/public quote; not suitable as a broker execution price.'}

class LicensedPlaceholderAdapter(BaseAdapter):
    def __init__(self,info):self.info=info
    def _configured(self):
        return bool(self.info.env_key and os.getenv(self.info.env_key))
    def status(self):
        return {'id':self.info.id,'name':self.info.name,
                'status':'ADAPTER_IMPLEMENTATION_REQUIRED' if self._configured() else 'NOT_CONFIGURED',
                'realtime':self.info.realtime,'depth':self.info.depth,'requires_license':self.info.requires_license,
                'credential_present':self._configured(),
                'note':'Provider slot only. No proprietary endpoint or protocol is guessed.'}
    def quote(self,ticker):
        return {'status':'UNAVAILABLE','provider':self.info.id,'ticker':ticker.upper().replace('.IS',''),
                'reason':'PROVIDER_ADAPTER_NOT_IMPLEMENTED','synthetic':False}
    def candles(self,ticker,period='1mo',interval='1d'):
        return {'status':'UNAVAILABLE','provider':self.info.id,'ticker':ticker.upper().replace('.IS',''),
                'reason':'PROVIDER_ADAPTER_NOT_IMPLEMENTED','synthetic':False}

_ADAPTERS={'yahoo_delayed':YahooDelayedAdapter()}
for x in CATALOG[1:]:_ADAPTERS[x.id]=LicensedPlaceholderAdapter(x)

def adapter(provider='yahoo_delayed')->BaseAdapter:
    key=str(provider or 'yahoo_delayed').lower()
    if key not in _ADAPTERS:raise ValueError('Unknown market-data provider')
    return _ADAPTERS[key]

def registry():
    rows=[_ADAPTERS[x.id].status() for x in CATALOG]
    connected=[x for x in rows if x.get('status') in {'AVAILABLE_DELAYED','CONNECTED'}]
    realtime=[x for x in rows if x.get('status')=='CONNECTED' and x.get('realtime')]
    return {'status':'OK','version':'124.0','default_provider':'yahoo_delayed','rows':rows,
            'connected_realtime':len(realtime),'connected_any':len(connected),
            'policy':'Real-time and depth are never inferred. Licensed adapters must be explicitly implemented and authenticated; delayed Yahoo remains a clearly labeled fallback.'}

def quote(ticker,provider='yahoo_delayed'):
    return adapter(provider).quote(ticker)

def candles(ticker,provider='yahoo_delayed',period='1mo',interval='1d'):
    return adapter(provider).candles(ticker,period,interval)

def depth(ticker,provider='yahoo_delayed'):
    a=adapter(provider)
    if not a.info.depth:
        return {'status':'UNAVAILABLE','provider':a.info.id,'ticker':ticker.upper().replace('.IS',''),
                'reason':'PROVIDER_DOES_NOT_SUPPORT_DEPTH','synthetic':False}
    if a.status().get('status')!='CONNECTED':
        return {'status':'UNAVAILABLE','provider':a.info.id,'ticker':ticker.upper().replace('.IS',''),
                'reason':'LICENSED_DEPTH_FEED_NOT_CONNECTED','synthetic':False}
    return a.depth_snapshot(ticker)
