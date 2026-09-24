from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List
from .kap_engine import company_profile, disclosures

def _date(s):
    try:return datetime.strptime(s,'%d.%m.%Y')
    except Exception:return None

def catalyst_calendar(codes:List[str]):
    codes=list(dict.fromkeys([x.upper().replace('.IS','') for x in codes if x]))[:16]
    events=[]
    def load(code):
        return code,company_profile(code),disclosures(code,6)
    with ThreadPoolExecutor(max_workers=6) as ex:
        fut=[ex.submit(load,c) for c in codes]
        for f in as_completed(fut):
            try:
                code,p,d=f.result()
                for x in p.get('calendar') or []:
                    dt=_date(x.get('start'))
                    events.append({'ticker':code,'type':'FINANCIAL_CALENDAR','date':x.get('start'),'date_sort':dt.timestamp() if dt else 9e18,
                                   'title':x.get('subject') or 'Finansal rapor','detail':f"{x.get('period','')} {x.get('year','')}".strip(),
                                   'end':x.get('end'),'source':'KAP','url':p.get('url'),'materiality':80})
                for x in (d.get('items') or [])[:4]:
                    events.append({'ticker':code,'type':x.get('event'),'date':None,'date_sort':0,'title':x.get('title'),
                                   'detail':x.get('summary','')[:220],'source':'KAP public search','url':x.get('url'),
                                   'materiality':x.get('materiality',25),'sentiment_score':x.get('sentiment_score',0)})
            except Exception:pass
    events.sort(key=lambda x:(x.get('date_sort',9e18),-(x.get('materiality') or 0)))
    for x in events:x.pop('date_sort',None)
    return {'codes':codes,'count':len(events),'events':events}
