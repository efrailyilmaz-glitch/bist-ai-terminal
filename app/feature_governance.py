"""V47 adaptive feature governance.
Builds a conservative challenger from forward-only attribution.
Production/champion logic is never silently mutated.
"""
from __future__ import annotations
import time, threading
from .decision_attribution import attribution
from .protected_feature_governance import apply as apply_protected_governance

_LOCK=threading.Lock()
_CACHE={'at':0.0,'report':None}
TTL=10*60

def _rows_by_horizon(min_samples=12):
    out={}
    for h in (5,20,60):
        r=attribution(h,min_samples=min_samples)
        out[h]={x['feature']:x for x in (r.get('rows') or [])}
    return out

def governance_report(force=False):
    now=time.time()
    with _LOCK:
        if not force and _CACHE['report'] is not None and now-_CACHE['at']<TTL:
            return _CACHE['report']
    byh=_rows_by_horizon(12)
    feats=sorted(set().union(*[set(x) for x in byh.values()])) if byh else []
    rows=[]
    for f in feats:
        evidence=[]
        neg=cons=0;max_n=0;weighted_delta=[]
        for h in (5,20,60):
            x=byh[h].get(f)
            if not x:continue
            n=int(x.get('with_n') or 0);max_n=max(max_n,n)
            lab=x.get('label');d=x.get('delta_mean_excess_pct')
            evidence.append({'horizon':h,'with_n':n,'label':lab,'delta_mean_excess_pct':d,
                             'delta_ci_low':x.get('delta_ci_low'),'delta_ci_high':x.get('delta_ci_high'),
                             'fdr_q_value':x.get('fdr_q_value'),'regime_conflict':x.get('regime_conflict')})
            if lab=='NEGATIVE':neg+=1
            if lab=='CONSISTENT':cons+=1
            if d is not None and n>=12:weighted_delta.append((float(d),n))
        avg_delta=(sum(d*n for d,n in weighted_delta)/sum(n for _,n in weighted_delta)) if weighted_delta else None
        # Governance states are intentionally hard to escalate and easy to leave unchanged.
        state='OBSERVE';mult=1.0;reason='Insufficient persistent negative forward evidence.'
        if cons>=2 and neg==0 and max_n>=30:
            state='SUPPORTED';reason='Positive forward association across multiple horizons; no risk boost is granted.'
        elif neg>=1 and max_n>=30:
            state='QUARANTINE';mult=.85;reason='At least one forward horizon is negative with >=30 observations.'
        if neg>=2 and max_n>=50:
            state='DOWNWEIGHT';mult=.65;reason='Persistent negative association across >=2 horizons with >=50 observations.'
        if neg>=2 and max_n>=80 and (avg_delta is not None and avg_delta<=-1.0):
            state='CHALLENGER_DISABLE';mult=0.0;reason='Strong persistent negative forward evidence; disable only in challenger.'
        if cons>=1 and neg>=1:
            state='CONFLICTED';mult=1.0;reason='Horizon evidence conflicts; no automatic penalty.'
        rows.append({'feature':f,'state':state,'challenger_multiplier':mult,'max_with_n':max_n,
                     'negative_horizons':neg,'consistent_horizons':cons,
                     'weighted_delta_mean_excess_pct':None if avg_delta is None else round(avg_delta,3),
                     'evidence':evidence,'reason':reason})
    rows=apply_protected_governance(rows)
    order={'CHALLENGER_DISABLE':0,'DOWNWEIGHT':1,'QUARANTINE':2,'PROTECTED':3,'CONFLICTED':4,'OBSERVE':5,'SUPPORTED':6}
    rows.sort(key=lambda x:(order.get(x['state'],9),x['feature']))
    report={'status':'OK','rows':rows,
            'summary':{s:sum(1 for x in rows if x['state']==s) for s in order},
            'policy':'Champion remains unchanged. Protected safety/integrity features cannot be penalized. Other governance penalties apply only to challenger scoring and require persistent new forward evidence.'}
    with _LOCK:_CACHE.update({'at':now,'report':report})
    return report

def multiplier(feature):
    rep=governance_report()
    row=next((x for x in rep.get('rows',[]) if x['feature']==feature),None)
    return 1.0 if not row else float(row.get('challenger_multiplier',1.0))

def challenger_adjustment(confirmations,components):
    """Return score delta for challenger only. Never positive."""
    delta=0.0;details=[]
    # Confirmation bonuses in opportunity_engine are mostly 2-6 points. Penalize only
    # the unsupported portion; this cannot increase challenger score.
    bonus_guess={
      'Breakout + hacim':6,'Supertrend bullish':3,'Ichimoku bullish':3,'XU100 relative strength':4,
      'ADX trend teyidi':3,'Bullish divergence':3,'Kalite faktörü güçlü':3,'Büyüme faktörü güçlü':2,
      'Analist hedef desteği':3,'Pozitif KAP katalizörü':3
    }
    for name in confirmations or []:
        f='confirm:'+str(name);m=multiplier(f)
        if m<1:
            lost=bonus_guess.get(name,2)*(1-m);delta-=lost
            details.append({'feature':f,'multiplier':m,'score_delta':round(-lost,3)})
    for k,v in (components or {}).items():
        try:z=float(v)
        except Exception:continue
        f='component:'+str(k)+(':high' if z>=70 else ':low' if z<=30 else '')
        if not f.endswith((':high',':low')):continue
        m=multiplier(f)
        if m<1:
            # Components are already blended; apply a modest challenger-only penalty.
            lost=(1-m)*2.0;delta-=lost
            details.append({'feature':f,'multiplier':m,'score_delta':round(-lost,3)})
    return {'score_delta':round(min(0.0,delta),3),'details':details}


def ab_report(horizon=20,threshold=78,min_samples=20):
    """Forward champion-vs-governance-challenger shadow comparison.
    Challenger may only reject/downscore; it never creates extra accepted signals.
    """
    if horizon not in (5,20,60):raise ValueError('horizon must be 5, 20 or 60')
    import json
    from . import experience_engine as ex
    with ex._LOCK:
        db=ex._conn();db.row_factory=__import__('sqlite3').Row
        rows=[dict(x) for x in db.execute(f'''SELECT opportunity_score,setup_json,excess_{horizon} AS excess
                                              FROM signals WHERE settled_{horizon}=1 AND excess_{horizon} IS NOT NULL''').fetchall()];db.close()
    champ=[];chall=[];rejected=[]
    for r in rows:
        try:s=json.loads(r.get('setup_json') or '{}')
        except Exception:s={}
        cs=r.get('opportunity_score');gs=s.get('governance_challenger_score')
        if not isinstance(cs,(int,float)) or not isinstance(gs,(int,float)):continue
        x=float(r['excess'])
        if float(cs)>=threshold:champ.append(x)
        if float(gs)>=threshold:chall.append(x)
        elif float(cs)>=threshold:rejected.append(x)
    def stats(a):
        if not a:return {'n':0}
        return {'n':len(a),'mean_excess_pct':round(sum(a)/len(a),3),
                'median_excess_pct':round(__import__('statistics').median(a),3),
                'hit_rate_pct':round(sum(1 for x in a if x>0)/len(a)*100,1)}
    cs,hs,rs=stats(champ),stats(chall),stats(rejected)
    status='INSUFFICIENT_DATA'
    recommendation='KEEP_CHAMPION'
    if hs['n']>=min_samples and rs['n']>=min_samples:
        status='OK'
        # Promotion only when rejected names are clearly harmful and challenger subset
        # has at least as good forward mean. No auto-promotion is performed.
        if rs.get('mean_excess_pct',0)<0 and hs.get('mean_excess_pct',-999)>=cs.get('mean_excess_pct',-999):
            recommendation='CHALLENGER_ELIGIBLE_FOR_PROMOTION_REVIEW'
    return {'status':status,'horizon':horizon,'threshold':threshold,'champion':cs,'challenger':hs,
            'champion_only_rejected_by_challenger':rs,'recommendation':recommendation,
            'note':'Shadow A/B on prospective settled signals. Recommendation never auto-promotes or changes production scoring.'}
