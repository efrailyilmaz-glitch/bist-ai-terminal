"""V96 prospective confidence calibration for committee-selected signals.
Committee score is treated as nominal confidence only for calibration diagnostics;
it is not assumed to be a true probability until forward evidence supports it.
"""
from __future__ import annotations
import math
from . import experience_engine as ex

BINS=[(0,50),(50,60),(60,70),(70,80),(80,90),(90,101)]

def analyze(horizon=20,success_excess_pct=0.0,min_bin=5):
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    threshold=float(success_excess_pct)
    with ex._LOCK:
        c=ex._conn();c.row_factory=__import__('sqlite3').Row
        rows=[dict(x) for x in c.execute(f'''SELECT id,ticker,committee_decision,committee_score,regime,excess_{horizon} AS excess
          FROM signals
          WHERE settled_{horizon}=1 AND excess_{horizon} IS NOT NULL
            AND committee_score IS NOT NULL AND committee_decision IN ('PASS','WATCH')
          ORDER BY id''').fetchall()]
        c.close()
    pts=[]
    for r in rows:
        p=max(0.0,min(1.0,float(r['committee_score'])/100.0))
        y=1.0 if float(r['excess'])>threshold else 0.0
        pts.append((p,y,r))
    brier=sum((p-y)**2 for p,y,_ in pts)/len(pts) if pts else None
    bins=[];ece=0.0
    for lo,hi in BINS:
        xs=[(p,y,r) for p,y,r in pts if lo<=p*100<hi]
        if not xs:continue
        avgp=sum(p for p,_,_ in xs)/len(xs)
        hit=sum(y for _,y,_ in xs)/len(xs)
        gap=avgp-hit;ece+=len(xs)/max(1,len(pts))*abs(gap)
        if len(xs)<int(min_bin):label='INSUFFICIENT'
        elif gap>=.10:label='OVERCONFIDENT'
        elif gap<=-.10:label='UNDERCONFIDENT'
        else:label='CALIBRATED'
        bins.append({'range':f'{lo}-{hi-1}','n':len(xs),'avg_confidence_pct':round(avgp*100,2),
                     'realized_success_pct':round(hit*100,2),'calibration_gap_pct':round(gap*100,2),'label':label})
    overall_hit=sum(y for _,y,_ in pts)/len(pts)*100 if pts else None
    overall_conf=sum(p for p,_,_ in pts)/len(pts)*100 if pts else None
    gap=None if overall_hit is None else overall_conf-overall_hit
    status='INSUFFICIENT' if len(pts)<max(12,int(min_bin)*2) else 'OVERCONFIDENT' if gap is not None and gap>=8 else 'UNDERCONFIDENT' if gap is not None and gap<=-8 else 'CALIBRATED'
    return {'status':status,'version':'96.0','horizon':horizon,'success_excess_threshold_pct':threshold,'settled_selected':len(pts),
            'overall_confidence_pct':None if overall_conf is None else round(overall_conf,2),
            'overall_success_pct':None if overall_hit is None else round(overall_hit,2),
            'overall_gap_pct':None if gap is None else round(gap,2),
            'brier_score':None if brier is None else round(brier,5),'expected_calibration_error':round(ece,5),
            'bins':bins,'live_execution':False,
            'policy':'Forward reliability diagnostic only. Committee score is not automatically rescaled; any confidence mapping change requires separate prospective shadow validation.'}
