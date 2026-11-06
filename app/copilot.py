"""V129 BIST AI Copilot.
OpenAI calls are server-side only. The renderer never receives the API key.
The assistant consumes compact terminal context and conditionally enriches it with local engines.
"""
from __future__ import annotations
import json,os,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

from .runtime_paths import data_path
from .market_data import scan_codes, market_overview
from .fundamentals import get_fundamentals
from .kap_engine import company_profile, disclosures
from .investment_committee import investment_committee

_SETTINGS=data_path('copilot_settings.json')
_DEFAULT_MODEL='gpt-6-luna'
_SESSION=requests.Session()
_SESSION.headers.update({'User-Agent':'BIST-AI-Terminal/129 Copilot'})

def _read_settings():
    try:
        d=json.loads(_SETTINGS.read_text(encoding='utf-8'))
        return d if isinstance(d,dict) else {}
    except Exception:return {}

def _key():
    return (os.getenv('OPENAI_API_KEY') or _read_settings().get('api_key') or '').strip()

def _model():
    return (os.getenv('OPENAI_MODEL') or _read_settings().get('model') or _DEFAULT_MODEL).strip()

def status():
    key=_key()
    return {
      'status':'READY' if key else 'NOT_CONFIGURED',
      'configured':bool(key),'model':_model(),'version':'129.0',
      'storage':'ENV' if os.getenv('OPENAI_API_KEY') else ('LOCAL_DESKTOP' if key else 'NONE'),
      'policy':'API key is never returned to the renderer. Copilot is research-only and cannot place broker orders.'
    }

def save_desktop_config(api_key:str|None=None,model:str|None=None):
    if os.getenv('BIST_AI_DESKTOP')!='1':
        return {'status':'BLOCKED','reason':'LOCAL_DESKTOP_ONLY'}
    old=_read_settings()
    key=str(api_key or '').strip()
    if key:
        old['api_key']=key
    elif api_key is not None:
        old.pop('api_key',None)
    if model is not None and str(model).strip():
        old['model']=str(model).strip()
    _SETTINGS.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
    try:os.chmod(_SETTINGS,0o600)
    except Exception:pass
    return status()

def _safe(fn,default=None):
    try:return fn()
    except Exception:return default

def _terminal_context(ticker:str,view:str,message:str,client:dict|None=None):
    ticker=(ticker or 'ASELS').upper().replace('.IS','')
    msg=(message or '').lower()
    client=client if isinstance(client,dict) else {}
    need_committee=any(x in msg for x in ['karar','al','sat','committee','komite','neden','risk','stop','hedef']) or view in {'committee','decisiongate','unifieddecision'}
    need_fund=any(x in msg for x in ['temel','bilanço','bilanco','f/k','fk','pd/dd','finansal','fundamental']) or view in {'fundamental','fundpricefusion'}
    need_kap=any(x in msg for x in ['kap','haber','açıklama','aciklama','bildirim']) or view in {'kap','catalysts','eventstudy'}
    jobs={
      'scan':lambda:_safe(lambda:(scan_codes([ticker]) or [None])[0]),
      'market':lambda:_safe(market_overview,{})
    }
    if need_committee:jobs['committee']=lambda:_safe(lambda:investment_committee(ticker),{})
    if need_fund:jobs['fundamentals']=lambda:_safe(lambda:get_fundamentals(ticker),{})
    if need_kap:
        jobs['kap_profile']=lambda:_safe(lambda:company_profile(ticker),{})
        jobs['kap_recent']=lambda:_safe(lambda:disclosures(ticker,limit=8),{})
    out={}
    with ThreadPoolExecutor(max_workers=min(4,len(jobs))) as ex:
        fut={ex.submit(fn):name for name,fn in jobs.items()}
        for future,name in fut.items():
            try:out[name]=future.result(timeout=18)
            except Exception:out[name]=None
    out['active_ticker']=ticker
    out['active_view']=view
    out['client']={
      'watchlist':(client.get('watchlist') or [])[:30],
      'gainers':(client.get('gainers') or [])[:8],
      'losers':(client.get('losers') or [])[:8],
      'visible_summary':client.get('visible_summary') or {}
    }
    return out

def _compact(obj,max_chars=18000):
    raw=json.dumps(obj,ensure_ascii=False,default=str,separators=(',',':'))
    return raw[:max_chars]

def _history_items(history):
    out=[]
    for x in (history or [])[-10:]:
        if not isinstance(x,dict):continue
        role='assistant' if x.get('role')=='assistant' else 'user'
        text=str(x.get('content') or '')[:3500]
        if text:out.append({'role':role,'content':text})
    return out

def _extract_text(data):
    if isinstance(data.get('output_text'),str) and data['output_text'].strip():
        return data['output_text'].strip()
    parts=[]
    for item in data.get('output') or []:
        if not isinstance(item,dict) or item.get('type')!='message':continue
        for c in item.get('content') or []:
            if isinstance(c,dict) and c.get('type')=='output_text' and c.get('text'):
                parts.append(str(c['text']))
    return '\n'.join(parts).strip()

def chat(message:str,ticker='ASELS',view='overview',history=None,client_context=None):
    key=_key()
    if not key:
        return {'status':'NOT_CONFIGURED','answer':'OpenAI API anahtarı yapılandırılmamış. Copilot ayarlarından anahtarı ekleyin.','configured':False}
    message=str(message or '').strip()
    if not message:return {'status':'ERROR','answer':'Mesaj boş olamaz.'}
    ctx=_terminal_context(ticker,view,message,client_context)
    instructions="""Sen BIST AI Terminal içindeki araştırma copilotu olarak çalışıyorsun.
Yalnız sana verilen terminal bağlamındaki verileri gerçekmiş gibi sun. Veri yoksa açıkça 'veri yok' de.
Yatırım garantisi verme, kesin kazanç iddia etme ve manipülasyon niyeti uydurma.
Signal Guard, Trap Defense, Committee ve risk veto'larını görmezden gelme.
Kullanıcı kısa bir soru sorarsa kısa cevap ver; analiz isterse gerekçeleri maddeleyerek açıkla.
Aktif hisseyi ve açık ekranı bağlam olarak kullan. Fiyatların gecikmeli olabileceğini gerektiğinde belirt.
Gerçek broker emri veremezsin; yalnız araştırma ve paper/sandbox akışını açıklayabilirsin.
Yanıt dili Türkçe olsun."""
    items=_history_items(history)
    items.append({'role':'user','content':f"TERMINAL_CONTEXT={_compact(ctx)}\n\nKULLANICI_SORUSU={message}"})
    payload={'model':_model(),'instructions':instructions,'input':items,'max_output_tokens':900}
    try:
        r=_SESSION.post('https://api.openai.com/v1/responses',
          headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},
          json=payload,timeout=45)
        if r.status_code>=400:
            detail=''
            try:detail=(r.json().get('error') or {}).get('message') or ''
            except Exception:detail=r.text[:300]
            return {'status':'API_ERROR','answer':f'AI servisi yanıt vermedi ({r.status_code}). {detail[:240]}','configured':True}
        data=r.json();answer=_extract_text(data)
        return {'status':'OK','answer':answer or 'Model metin yanıtı üretmedi.','configured':True,
                'model':data.get('model') or _model(),'response_id':data.get('id'),
                'ticker':ticker.upper().replace('.IS',''),'generated_epoch':time.time()}
    except requests.Timeout:
        return {'status':'TIMEOUT','answer':'AI yanıtı zaman aşımına uğradı. Tekrar deneyin.','configured':True}
    except Exception as e:
        return {'status':'ERROR','answer':f'Copilot hatası: {str(e)[:220]}','configured':True}
