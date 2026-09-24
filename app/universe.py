from __future__ import annotations
import re, threading, time
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

KAP_BIST_URL = 'https://www.kap.org.tr/tr/bist-sirketler'
_LOCK = threading.Lock()
_CACHE = {'ts': 0.0, 'rows': []}
FALLBACK = [
 ('ASELS','ASELSAN ELEKTRONİK SANAYİ VE TİCARET A.Ş.'),('THYAO','TÜRK HAVA YOLLARI A.O.'),
 ('TUPRS','TÜPRAŞ-TÜRKİYE PETROL RAFİNERİLERİ A.Ş.'),('KCHOL','KOÇ HOLDİNG A.Ş.'),
 ('BIMAS','BİM BİRLEŞİK MAĞAZALAR A.Ş.'),('FROTO','FORD OTOMOTİV SANAYİ A.Ş.'),
 ('GARAN','TÜRKİYE GARANTİ BANKASI A.Ş.'),('AKBNK','AKBANK T.A.Ş.'),('ISCTR','TÜRKİYE İŞ BANKASI A.Ş.'),
 ('YKBNK','YAPI VE KREDİ BANKASI A.Ş.'),('SISE','TÜRKİYE ŞİŞE VE CAM FABRİKALARI A.Ş.'),
 ('EREGL','EREĞLİ DEMİR VE ÇELİK FABRİKALARI T.A.Ş.'),('SAHOL','HACI ÖMER SABANCI HOLDİNG A.Ş.'),
 ('TCELL','TURKCELL İLETİŞİM HİZMETLERİ A.Ş.'),('PGSUS','PEGASUS HAVA TAŞIMACILIĞI A.Ş.')]

def _parse(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, 'html.parser')
    rows=[]; seen=set()
    for tr in soup.select('tr'):
        cells=[re.sub(r'\s+',' ',x.get_text(' ',strip=True)) for x in tr.select('td')]
        if len(cells) < 2: continue
        code=cells[0].strip().upper(); name=cells[1].strip()
        if not re.fullmatch(r'[A-Z0-9]{3,6}', code): continue
        if code in seen: continue
        seen.add(code)
        rows.append({'ticker':code,'name':name or code,'city':cells[2] if len(cells)>2 else '', 'source':'KAP'})
    return rows

def get_universe(force: bool=False) -> List[Dict]:
    now=time.time()
    with _LOCK:
        if _CACHE['rows'] and not force and now-_CACHE['ts'] < 12*3600:
            return _CACHE['rows']
    try:
        r=requests.get(KAP_BIST_URL,headers={'User-Agent':'Mozilla/5.0 BIST-AI-Terminal/3.0'},timeout=20)
        r.raise_for_status(); rows=_parse(r.text)
        if len(rows) >= 300:
            with _LOCK: _CACHE.update({'ts':now,'rows':rows})
            return rows
    except Exception:
        pass
    with _LOCK:
        if _CACHE['rows']: return _CACHE['rows']
    return [{'ticker':t,'name':n,'city':'','source':'FALLBACK'} for t,n in FALLBACK]
