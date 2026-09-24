from __future__ import annotations
import re, threading, time
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET
import requests
from .universe import find_company

_LOCK=threading.Lock();_CACHE={};TTL=20*60
UA={'User-Agent':'Mozilla/5.0 BIST-AI-Terminal/4.0'}
POS=['rekor','artış','büyüme','yatırım','sözleşme','ihale','sipariş','kapasite','temettü','geri alım','kâr','kar açıkladı','ihracat','teşvik','anlaşma','hedef yükseltti']
NEG=['düşüş','zarar','ceza','soruşturma','dava','yangın','üretim durdu','temerrüt','borç','hedef düşürdü','satış baskısı','işlem yasağı','devre kesici','iflas','konkordato']

def _txt(s):return re.sub(r'\s+',' ',(s or '')).strip()

def score_headline(title):
    low=title.lower();pos=[x for x in POS if x in low];neg=[x for x in NEG if x in low]
    score=max(-100,min(100,25*len(pos)-25*len(neg)))
    return score,pos[:4],neg[:4]

def headlines(ticker:str,limit:int=15):
    code=ticker.upper().replace('.IS','');now=time.time()
    with _LOCK:
        hit=_CACHE.get(code)
        if hit and now-hit[0]<TTL:return hit[1]
    meta=find_company(code) or {};name=meta.get('name') or code
    short=re.sub(r'\b(A\.Ş\.|AŞ|SANAYİ|TİCARET|VE)\b',' ',name,flags=re.I)
    short=_txt(short)[:55]
    query=quote_plus(f'"{short}" OR {code} Borsa')
    url=f'https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr'
    rows=[]
    try:
        r=requests.get(url,headers=UA,timeout=15);r.raise_for_status()
        root=ET.fromstring(r.content)
        for item in root.findall('.//item')[:limit]:
            title=_txt(item.findtext('title'));link=_txt(item.findtext('link'));pub=_txt(item.findtext('pubDate'))
            src=item.find('source');source=_txt(src.text if src is not None else '')
            s,p,n=score_headline(title)
            rows.append({'title':title,'url':link,'published':pub,'source':source,'sentiment_score':s,'positive_hits':p,'negative_hits':n})
    except Exception:
        pass
    vals=[x['sentiment_score'] for x in rows]
    avg=round(sum(vals)/len(vals),1) if vals else None
    out={'ticker':code,'status':'OK' if rows else 'NO_DATA','source':'Google News RSS','headline_sentiment':avg,'items':rows,
         'note':'Headline-only lexicon signal; article body is not scored.'}
    with _LOCK:_CACHE[code]=(now,out)
    return out
