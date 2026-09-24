from __future__ import annotations
import re, threading, time
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
from .universe import find_company

_LOCK=threading.Lock()
_CACHE={}
TTL=30*60
UA={'User-Agent':'Mozilla/5.0 BIST-AI-Terminal/4.0'}

POS={
 'NEW_ORDER':['yeni iş ilişkisi','sözleşme','sipariş','ihale kazandı','ihale sonucu','iş anlaşması'],
 'INVESTMENT':['yatırım','kapasite artışı','teşvik belgesi','yeni tesis','üretim kapasitesi'],
 'SHAREHOLDER_RETURN':['pay geri alım','geri alım','kar payı','kâr payı','temettü'],
 'CAPITAL_ACTION_POSITIVE':['bedelsiz sermaye art','iç kaynaklardan sermaye art','pay geri alım programı'],
 'OWNERSHIP':['pay alım','pay satım','ortaklık oranı','yönetici pay'],
 'FINANCING_POSITIVE':['kredi derecelendirme notu art','not artır','borç refinansman']
}
NEG={
 'LEGAL':['dava','soruşturma','inceleme','ceza','idari para cezası','işlem yasağı'],
 'OPERATIONS':['üretime ara','üretim dur','yangın','kaza','hasar','faaliyet dur'],
 'FINANCING_RISK':['temerrüt','borç yapılandır','ödeme güçlüğü','konkordato'],
 'MARKET_EVENT':['devre kesici','açığa satışta yukarı adım'],
 'CAPITAL_ACTION_RISK':['bedelli sermaye art','nakit sermaye art','sermaye azaltımı']
}

def _norm(s):
    return re.sub(r'\s+',' ',(s or '')).strip()

def classify(text:str):
    low=(text or '').lower()
    hits=[];score=0;event='OTHER'
    for e,words in POS.items():
        h=[w for w in words if w in low]
        if h:
            hits+=h;score+=min(60,20+10*len(h));event=e
    for e,words in NEG.items():
        h=[w for w in words if w in low]
        if h:
            hits+=h;score-=min(65,22+10*len(h));event=e
    score=max(-100,min(100,score))
    materiality=25+min(60,len(hits)*18)
    if any(x in low for x in ['sözleşme','ihale','yatırım','dava','ceza','temerrüt','yangın']):materiality+=10
    return {'event':event,'sentiment_score':score,'materiality':min(100,materiality),'keywords':hits[:5]}

def _between(text,start,end):
    i=text.find(start)
    if i<0:return ''
    i+=len(start);j=text.find(end,i)
    return _norm(text[i:j if j>=0 else None])

def company_profile(ticker:str,force:bool=False):
    code=ticker.upper().replace('.IS','')
    key='profile:'+code;now=time.time()
    with _LOCK:
        hit=_CACHE.get(key)
        if hit and not force and now-hit[0]<TTL:return hit[1]
    meta=find_company(code) or {}
    url=meta.get('kap_url')
    out={'ticker':code,'status':'NO_PROFILE','source':'KAP','url':url,'sectors':[],'indices':[],'market':None,'calendar':[]}
    if not url:return out
    try:
        r=requests.get(url,headers=UA,timeout=20);r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        text=_norm(soup.get_text(' ',strip=True))
        idx_txt=_between(text,'Şirketin Dahil Olduğu Endeksler','Şirketin Sektörü')
        sec_txt=_between(text,'Şirketin Sektörü','Sermaye Piyasası Aracının İşlem Gördüğü Pazar')
        market_txt=_between(text,'Sermaye Piyasası Aracının İşlem Gördüğü Pazar','Esas Sözleşme')
        indices=re.findall(r'BIST [A-ZÇĞİÖŞÜ0-9 ]{2,40}',idx_txt)
        indices=list(dict.fromkeys([_norm(x) for x in indices]))[:20]
        sectors=[]
        for a in soup.find_all('a'):
            txt=_norm(a.get_text(' ',strip=True))
            href=a.get('href','')
            if '/Sektorler' in href or '/sektorler' in href:
                if txt and txt not in sectors:sectors.append(txt)
        market=None
        for a in soup.find_all('a'):
            txt=_norm(a.get_text(' ',strip=True))
            if 'PAZAR' in txt.upper() and len(txt)<60:
                market=txt;break
        if not market and market_txt:market=market_txt[:80]
        cal=[]
        for tr in soup.select('tr'):
            cells=[_norm(td.get_text(' ',strip=True)) for td in tr.select('td')]
            if len(cells)>=6 and any(re.fullmatch(r'\d{2}\.\d{2}\.\d{4}',x) for x in cells):
                dates=[x for x in cells if re.fullmatch(r'\d{2}\.\d{2}\.\d{4}',x)]
                if dates:
                    cal.append({'subject':cells[2] if len(cells)>2 else '','period':cells[3] if len(cells)>3 else '',
                                'year':cells[4] if len(cells)>4 else '','start':dates[0],'end':dates[-1]})
        out.update({'status':'OK','sectors':sectors[:8],'indices':indices,'market':market,'calendar':cal[:10],
                    'city':meta.get('city'),'auditor':meta.get('auditor')})
    except Exception as e:
        out['error']=str(e)[:160]
    with _LOCK:_CACHE[key]=(now,out)
    return out

def disclosures(ticker:str,limit:int=12):
    code=ticker.upper().replace('.IS','');key='disc:'+code;now=time.time()
    with _LOCK:
        hit=_CACHE.get(key)
        if hit and now-hit[0]<TTL:return hit[1]
    meta=find_company(code) or {};name=(meta.get('name') or code).split(' A.Ş.')[0]
    url=f'https://www.kap.org.tr/tr/search/{quote(code)}/3'
    items=[];seen=set()
    try:
        r=requests.get(url,headers=UA,timeout=20);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser')
        for a in soup.select('a[href*="/Bildirim/"],a[href*="/bildirim/"]'):
            href=a.get('href','')
            if not href or href in seen:continue
            seen.add(href)
            parent=a
            for _ in range(3):
                if parent.parent is not None:parent=parent.parent
            text=_norm(parent.get_text(' ',strip=True))
            low=text.lower()
            if 'portföy dağılım raporu' in low or 'fon' in low and code.lower() not in low:continue
            if code.lower() not in low and name.lower()[:12] not in low:continue
            title=_norm(a.get_text(' ',strip=True)) or text[:150]
            analysis=classify(text)
            items.append({'title':title[:220],'summary':text[:500],'url':'https://www.kap.org.tr'+href if href.startswith('/') else href,**analysis})
            if len(items)>=limit:break
    except Exception:
        pass
    result={'ticker':code,'status':'OK' if items else 'NO_MATCH','source':'KAP public search','items':items}
    with _LOCK:_CACHE[key]=(now,result)
    return result
