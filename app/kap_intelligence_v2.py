"""V109 KAP Intelligence 2.0.
Combines richer KAP event taxonomy with descriptive 1/5/20-day stock-vs-XU100 event outcomes.
Day-granular public-search dates are preserved; no intraday timing precision is invented.
"""
from __future__ import annotations
from collections import defaultdict
from .kap_engine import disclosures
from .alpha_engine import event_study
from .point_in_time import audit_disclosures

def analyze(ticker,limit=30):
    code=str(ticker).upper().replace('.IS','')
    disc=disclosures(code,limit=max(5,min(int(limit),50)))
    items=disc.get('items') or []
    pit=audit_disclosures(items)
    study=event_study(code,limit=max(5,min(int(limit),50)))
    events=study.get('events') or []
    groups=defaultdict(list)
    for e in events:
        groups[str(e.get('category') or 'OTHER')].append(e)
    categories=[]
    for cat,rows in groups.items():
        out={'category':cat,'n':len(rows)}
        for h in (1,5,20):
            vals=[float(x[f'excess_{h}d']) for x in rows if x.get(f'excess_{h}d') is not None]
            out[f'n_{h}d']=len(vals)
            out[f'mean_excess_{h}d']=None if not vals else round(sum(vals)/len(vals),3)
            out[f'hit_rate_{h}d']=None if not vals else round(sum(1 for x in vals if x>0)/len(vals)*100,1)
        mats=[float(x.get('materiality') or 0) for x in rows]
        out['avg_materiality']=round(sum(mats)/len(mats),1) if mats else None
        categories.append(out)
    categories.sort(key=lambda x:(-x['n'],-(x.get('avg_materiality') or 0),x['category']))
    recent=[]
    for it in items:
        recent.append({'date':it.get('date'),'event':it.get('event'),'title':it.get('title'),
                       'materiality':it.get('materiality'),'sentiment_score':it.get('sentiment_score'),
                       'keywords':it.get('keywords') or [],'url':it.get('url')})
    return {'ticker':code,'status':'OK' if items else 'NO_MATCH','version':'109.0','point_in_time':pit,
            'categories':categories,'recent':recent,'event_count':len(events),
            'source':disc.get('source'),'live_execution':False,
            'limits':'KAP public-search dates are day-granular here. Category event studies are descriptive gross price/excess returns; overlapping events, consensus surprise and exact publication-time effects are not controlled.'}
