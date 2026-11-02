"""V43 point-in-time integrity gates.
Rejects evidence that was not demonstrably available by observation time.
This module is deliberately conservative: uncertain timestamps downgrade or block
prospective evidence; they never improve a signal.
"""
from __future__ import annotations
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import math, time

TR=ZoneInfo('Europe/Istanbul')

def _epoch(x):
    if x is None:return None
    if isinstance(x,(int,float)):
        return float(x) if math.isfinite(float(x)) else None
    s=str(x).strip()
    if not s:return None
    try:
        dt=datetime.fromisoformat(s.replace('Z','+00:00'))
        if dt.tzinfo is None:dt=dt.replace(tzinfo=TR)
        return dt.timestamp()
    except Exception:
        try:
            d=datetime.strptime(s[:10],'%Y-%m-%d').replace(tzinfo=TR)
            return d.timestamp()
        except Exception:return None

def audit_signal(signal, observed_epoch=None, max_fetch_future_sec=120):
    """Audit whether a prospective signal only references information available now."""
    s=signal or {};obs=float(observed_epoch or time.time());flags=[];status='PASS'
    fetched=_epoch(s.get('fetched_at'));asof=_epoch(s.get('as_of'))
    if s.get('bar_provisional'):
        flags.append('PROVISIONAL_BAR');status='BLOCK'
    if fetched is None:
        flags.append('FETCH_TIMESTAMP_MISSING');status='CAUTION' if status=='PASS' else status
    elif fetched>obs+max_fetch_future_sec:
        flags.append('FETCHED_IN_FUTURE');status='BLOCK'
    if asof is None:
        flags.append('SOURCE_ASOF_MISSING');status='CAUTION' if status=='PASS' else status
    else:
        # Daily source dates are date-granular. A future calendar date is impossible evidence.
        obs_day=datetime.fromtimestamp(obs,TR).date()
        src_day=datetime.fromtimestamp(asof,TR).date()
        if src_day>obs_day:
            flags.append('SOURCE_ASOF_IN_FUTURE');status='BLOCK'
    guard=(s.get('signal_guard') or {}).get('status')
    if guard and guard not in {'CLEAR','OK'}:
        flags.append('SIGNAL_GUARD_'+str(guard))
        if status=='PASS':status='CAUTION'
    return {'status':status,'flags':flags,'observed_epoch':obs,
            'observed_at':datetime.fromtimestamp(obs,timezone.utc).isoformat(),
            'source_as_of':s.get('as_of'),'fetched_at':s.get('fetched_at'),
            'note':'Point-in-time availability gate. Missing/uncertain timestamps never count as positive evidence.'}

def audit_disclosures(items, observed_epoch=None):
    """Date-granular KAP/news sanity check. Does not invent publication timestamps."""
    obs=float(observed_epoch or time.time());today=datetime.fromtimestamp(obs,TR).date();flags=[];checked=0
    for x in items or []:
        raw=x.get('date')
        if not raw:continue
        checked+=1
        try:d=datetime.strptime(str(raw)[:10],'%d.%m.%Y').date()
        except Exception:
            try:d=datetime.fromisoformat(str(raw)[:10]).date()
            except Exception:flags.append('UNPARSEABLE_DATE');continue
        if d>today:flags.append('FUTURE_DISCLOSURE_DATE')
    return {'status':'BLOCK' if 'FUTURE_DISCLOSURE_DATE' in flags else ('CAUTION' if flags else 'PASS'),
            'checked':checked,'flags':flags,
            'note':'KAP public-search dates are only day-granular here; exact intraday publication-time integrity requires an official timestamped feed.'}
