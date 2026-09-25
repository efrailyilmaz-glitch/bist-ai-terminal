from __future__ import annotations
import io, re, statistics, threading, time
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET
import requests
import pandas as pd

_LOCK=threading.Lock();_CACHE={};_PAGE_CACHE={};TTL=6*3600
HTTP=requests.Session();HTTP.headers.update({'User-Agent':'Mozilla/5.0 BIST-AI-Terminal/6.0'})
IS_URL='https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/takip-listesi.aspx'
GEDIK_URL='https://gedik.com/analiz/model-portfoy/hisse-model-portfoy'
TRUSTED=['İş Yatırım','Is Yatirim','Gedik Yatırım','Gedik Yatirim','Garanti BBVA Yatırım','Garanti BBVA Yatirim','OYAK Yatırım','OYAK Yatirim','Yapı Kredi Yatırım','Yapi Kredi Yatirim','Deniz Yatırım','Deniz Yatirim','Ak Yatırım','Ak Yatirim']

def _text(x):return re.sub(r'\s+',' ',str(x if x is not None else '')).strip()
def _num(v):
    if v is None:return None
    s=_text(v).replace('₺','').replace('%','').replace('TL','').replace('\xa0','').strip()
    if not s or s in {'-','—','nan','NaN'}:return None
    s=re.sub(r'[^0-9,.\-]','',s)
    try:
        if ',' in s and '.' in s:s=s.replace('.','').replace(',','.') if s.rfind(',')>s.rfind('.') else s.replace(',','')
        elif ',' in s:s=s.replace('.','').replace(',','.')
        return float(s)
    except Exception:return None
def _norm_col(x):
    if isinstance(x,tuple):x=' '.join(_text(z) for z in x if _text(z).lower()!='nan')
    return _text(x).lower().replace('ı','i').replace('ş','s').replace('ğ','g').replace('ü','u').replace('ö','o').replace('ç','c')
def _tables(key,url):
    now=time.time()
    with _LOCK:
        h=_PAGE_CACHE.get(key)
        if h and now-h[0]<TTL:return h[1]
    try:
        r=HTTP.get(url,timeout=18);r.raise_for_status();t=pd.read_html(io.StringIO(r.text))
    except Exception:t=[]
    with _LOCK:_PAGE_CACHE[key]=(now,t)
    return t
def _find_col(df,terms,avoid=()):
    for c in df.columns:
        n=_norm_col(c)
        if all(t in n for t in terms) and not any(a in n for a in avoid):return c
    return None
def _find_row(tables,code):
    for df in tables:
        if df is None or df.empty:continue
        for c in df.columns:
            try:
                hit=df[df[c].astype(str).str.strip().str.upper()==code]
                if not hit.empty:return df,hit.iloc[0]
            except Exception:pass
    return None,None
def _isyatirim(code):
    df,row=_find_row(_tables('is',IS_URL),code)
    if row is None:return None
    rec=_find_col(df,['oneri'],['tarih']);date=_find_col(df,['oneri','tarih']);target=_find_col(df,['hedef','fiyat']);pot=_find_col(df,['potansiyel'])
    return {'institution':'İş Yatırım','source_type':'OFFICIAL_RESEARCH_TABLE','recommendation':_text(row.get(rec)) if rec is not None else None,
            'target_price':_num(row.get(target)) if target is not None else None,'published':_text(row.get(date)) if date is not None else None,
            'reported_upside_pct':_num(row.get(pot)) if pot is not None else None,'url':IS_URL}
def _gedik(code):
    df,row=_find_row(_tables('gedik',GEDIK_URL),code)
    if row is None:return None
    target=_find_col(df,['hedef','fiyat']);pot=_find_col(df,['potansiyel'])
    return {'institution':'Gedik Yatırım','source_type':'OFFICIAL_MODEL_PORTFOLIO','recommendation':'MODEL PORTFÖY',
            'target_price':_num(row.get(target)) if target is not None else None,'published':None,
            'reported_upside_pct':_num(row.get(pot)) if pot is not None else None,'url':GEDIK_URL}
def _headlines(code,limit=8):
    q=quote_plus(f'{code} ("İş Yatırım" OR "Gedik Yatırım" OR "Garanti BBVA Yatırım" OR "OYAK Yatırım" OR "Yapı Kredi Yatırım" OR "Deniz Yatırım" OR "Ak Yatırım")')
    url=f'https://news.google.com/rss/search?q={q}&hl=tr&gl=TR&ceid=TR:tr';rows=[]
    try:
        r=HTTP.get(url,timeout=15);r.raise_for_status();root=ET.fromstring(r.content)
        for item in root.findall('.//item')[:30]:
            title=_text(item.findtext('title'));src=item.find('source');source=_text(src.text if src is not None else '')
            if not any(n.lower() in (title+' '+source).lower() for n in TRUSTED):continue
            rows.append({'title':title,'url':_text(item.findtext('link')),'published':_text(item.findtext('pubDate')),'source':source})
            if len(rows)>=limit:break
    except Exception:pass
    return rows
def _bias(rec):
    s=_text(rec).upper()
    if any(x in s for x in ['SAT','ENDEKS ALTI','END. ALTI']):return -18
    if any(x in s for x in ['AL','ENDEKS ÜSTÜ','END. ÜSTÜ','EÜ','MODEL PORTFÖY','MODEL PORTFOY']):return 14
    return 0
def trusted_research(ticker,current_price=None,fundamentals=None,limit=8):
    code=ticker.upper().replace('.IS','');now=time.time()
    with _LOCK:
        h=_CACHE.get(code)
        if h and now-h[0]<TTL:
            out=dict(h[1])
            if current_price and out.get('consensus_target'):out['consensus_upside_pct']=round((out['consensus_target']/current_price-1)*100,1)
            return out
    sources=[]
    for fn in (_isyatirim,_gedik):
        try:
            x=fn(code)
            if x:sources.append(x)
        except Exception:pass
    f=fundamentals or {};yt=_num(f.get('target_mean_price'))
    if yt:sources.append({'institution':'Yahoo Finance analyst consensus','source_type':'AGGREGATED_CONSENSUS','recommendation':f.get('recommendation_key'),
                          'target_price':yt,'published':None,'reported_upside_pct':None,'analyst_count':f.get('analyst_count'),'url':f'https://finance.yahoo.com/quote/{code}.IS/'})
    targets=[x['target_price'] for x in sources if x.get('target_price') and x['target_price']>0]
    consensus=round(statistics.median(targets),2) if targets else None
    upside=round((consensus/current_price-1)*100,1) if consensus and current_price else None
    score=50+(max(-25,min(35,upside*.65)) if upside is not None else 0)+(max(-18,min(18,sum(_bias(x.get('recommendation')) for x in sources)/max(1,len(sources)))) if sources else 0)
    out={'ticker':code,'status':'OK' if sources else 'NO_STRUCTURED_COVERAGE','sources':sources,'consensus_target':consensus,'consensus_upside_pct':upside,
         'analyst_score':int(max(0,min(100,round(score)))),'coverage_count':len(sources),'headlines':_headlines(code,limit),
         'fetched_at':time.strftime('%d.%m.%Y %H:%M:%S'),'note':'Kaynak ve tarih gösterilen kamuya açık araştırma/consensus verileri; tam telifli rapor metinleri yeniden yayımlanmaz.'}
    with _LOCK:_CACHE[code]=(now,out)
    return out
