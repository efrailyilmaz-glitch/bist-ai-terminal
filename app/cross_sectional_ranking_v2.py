"""V111 cross-sectional ranking 2.0.
Ranks current BIST candidates relative to the same contemporaneous universe snapshot.
Low-coverage snapshots are blocked rather than producing a misleading leaderboard.
"""
from __future__ import annotations
import math
import numpy as np
from .universe import get_universe
from .market_data import scan_codes
from .data_quality_guard import audit_current_snapshot

def _f(x,d=0.0):
    try:
        z=float(x);return z if math.isfinite(z) else d
    except Exception:return d

def _pct(values,reverse=False):
    a=np.asarray(values,float);order=np.argsort(a)
    ranks=np.empty(len(a),float);ranks[order]=np.arange(len(a))
    p=100*ranks/max(1,len(a)-1)
    return 100-p if reverse else p

def rank(limit=600,min_coverage_pct=80.0):
    universe=get_universe();codes=[x.get('ticker') for x in universe if x.get('ticker')][:max(20,min(int(limit),700))]
    rows=scan_codes(codes)
    quality=audit_current_snapshot(rows,requested=len(codes),min_coverage_pct=min_coverage_pct)
    if quality.get('status')=='BLOCK':
        return {'status':'DATA_BLOCK','version':'111.0','quality':quality,'rows':[],'requested':len(codes),'received':len(rows)}
    clean=[r for r in rows if _f(r.get('price'))>0]
    if not clean:return {'status':'NO_DATA','version':'111.0','quality':quality,'rows':[]}
    metrics={
      'short':[ _f(r.get('short_score'),50) for r in clean],
      'long':[ _f(r.get('long_score'),50) for r in clean],
      'rs20':[ _f(r.get('relative_strength_20')) for r in clean],
      'rs60':[ _f(r.get('relative_strength_60')) for r in clean],
      'mom20':[ _f(r.get('momentum_20')) for r in clean],
      'risk':[ _f(r.get('risk'),100) for r in clean],
      'liq':[ math.log1p(max(0,_f(r.get('avg_value_turnover_20')))) for r in clean],
    }
    pct={k:_pct(v,reverse=(k=='risk')) for k,v in metrics.items()}
    out=[]
    for i,r in enumerate(clean):
        comp=.18*pct['short'][i]+.18*pct['long'][i]+.18*pct['rs20'][i]+.14*pct['rs60'][i]+.12*pct['mom20'][i]+.12*pct['risk'][i]+.08*pct['liq'][i]
        if (r.get('signal_guard') or {}).get('status') not in {None,'CLEAR'}:comp-=12
        if (r.get('trap_defense') or {}).get('status') in {'WAIT','BLOCK'}:comp-=15
        out.append({'ticker':r.get('ticker'),'relative_rank_score':round(max(0,min(100,comp)),2),
                    'short_pct':round(float(pct['short'][i]),1),'long_pct':round(float(pct['long'][i]),1),
                    'rs20_pct':round(float(pct['rs20'][i]),1),'rs60_pct':round(float(pct['rs60'][i]),1),
                    'momentum_pct':round(float(pct['mom20'][i]),1),'risk_quality_pct':round(float(pct['risk'][i]),1),
                    'liquidity_pct':round(float(pct['liq'][i]),1),'absolute_short_score':r.get('short_score'),
                    'absolute_long_score':r.get('long_score'),'price':r.get('price'),'risk':r.get('risk'),
                    'signal_guard':(r.get('signal_guard') or {}).get('status'),'trap_defense':(r.get('trap_defense') or {}).get('status')})
    out.sort(key=lambda x:(-x['relative_rank_score'],x['ticker'] or ''))
    for i,x in enumerate(out,1):x['rank']=i;x['universe_percentile']=round(100*(1-(i-1)/max(1,len(out))),2)
    return {'status':'OK','version':'111.0','requested':len(codes),'received':len(rows),'ranked':len(out),
            'quality':quality,'rows':out,
            'policy':'Current cross-sectional ranking only. Relative percentile is meaningful only within this same contemporaneous snapshot; low-coverage universes are blocked.'}
