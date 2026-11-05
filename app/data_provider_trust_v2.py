"""V108 Data Quality & Provider Trust 2.0.
Determines whether current evidence is trustworthy enough for a new research decision.
Critical market/universe failures block; secondary providers only downgrade.
"""
from __future__ import annotations
from datetime import datetime,timezone
import time
from .universe import get_universe
from .market_data import scan_codes,yahoo_rows
from .news_engine import headlines
from .data_quality_guard import audit_current_snapshot
from .pit_universe import dataset_status

def _age_hours(ts):
    try:
        if isinstance(ts,(int,float)):epoch=float(ts)
        else:
            dt=datetime.fromisoformat(str(ts).replace('Z','+00:00'))
            if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
            epoch=dt.timestamp()
        return max(0,(time.time()-epoch)/3600)
    except Exception:return None

def _last_market_age():
    rows=(yahoo_rows('XU100',period='1mo',interval='1d').get('candles') or [])
    if not rows:return None,0
    last=rows[-1];raw=last.get('time') or last.get('date')
    return _age_hours(raw),len(rows)

def snapshot(codes=None,min_coverage_pct=80.0):
    universe=get_universe();u_source=(universe[0].get('source') if universe else 'NONE')
    sample=list(dict.fromkeys([str(x).upper().replace('.IS','') for x in (codes or []) if x]))
    if not sample:sample=[x.get('ticker') for x in universe[:40] if x.get('ticker')]
    requested=len(sample);rows=[]
    try:rows=scan_codes(sample)
    except Exception:rows=[]
    quality=audit_current_snapshot(rows,requested=requested,min_coverage_pct=min_coverage_pct)
    age_h,candles=_last_market_age()
    providers=[]
    def add(name,status,critical,detail,score):
        providers.append({'provider':name,'status':status,'critical':bool(critical),'trust_score':max(0,min(100,int(score))),'detail':detail})
    kap_ok=bool(universe) and u_source=='KAP'
    add('KAP Universe','PASS' if kap_ok else 'BLOCK',True,{'count':len(universe),'source':u_source},100 if kap_ok else 0)
    market_ok=candles>=10 and age_h is not None and age_h<=96
    add('Yahoo XU100 Daily','PASS' if market_ok else 'BLOCK',True,{'candles':candles,'last_age_hours':None if age_h is None else round(age_h,1)},95 if market_ok else 10)
    add('Current Scan Coverage',quality.get('status'),True,quality.get('details') or {},100 if quality.get('status')=='PASS' else 55 if quality.get('status')=='CAUTION' else 0)
    try:
        n=headlines('ASELS',3);ns=n.get('status');news_ok=ns in {'OK','PARTIAL'}
        add('News RSS','PASS' if news_ok else 'CAUTION',False,{'status':ns},80 if news_ok else 40)
    except Exception as e:add('News RSS','CAUTION',False,{'error':str(e)[:120]},30)
    pit=dataset_status();pit_ok=pit.get('status')=='PIT_VERIFIED'
    add('Point-in-Time Universe','PASS' if pit_ok else 'CAUTION',False,{'status':pit.get('status'),'survivorship_bias_risk':pit.get('survivorship_bias_risk')},100 if pit_ok else 45)
    critical_blocks=[x for x in providers if x['critical'] and x['status']=='BLOCK']
    cautions=[x for x in providers if x['status']=='CAUTION']
    overall='DATA_BLOCK' if critical_blocks else 'CAUTION' if cautions else 'TRUSTED'
    trust=min((x['trust_score'] for x in providers if x['critical']),default=0)
    return {'status':overall,'version':'108.0','trust_score':trust,'requested_symbols':requested,'received_symbols':len(rows),
            'providers':providers,'current_quality':quality,'pit_universe':pit,
            'critical_blocks':[x['provider'] for x in critical_blocks],'cautions':[x['provider'] for x in cautions],
            'decision_allowed':not bool(critical_blocks),
            'policy':'Critical market/universe integrity failures block new research decisions. Secondary-source degradation is transparent caution and never positive evidence.'}
