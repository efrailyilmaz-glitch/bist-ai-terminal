"""V74 forward-evidence ensemble challenger lab.
Combines only mature prospective challenger snapshots on the same as-of date/common universe.
Research-only: no scheduler, paper order or broker path.
"""
from __future__ import annotations
import math
import numpy as np
from .model_registry import register as register_artifact

def _f(x,default=0.0):
    try:
        z=float(x);return z if math.isfinite(z) else default
    except Exception:return default

def evidence_gate(candidate):
    e=(candidate or {}).get('forward_evidence') or {}
    reasons=[]
    if int(e.get('days') or 0)<90:reasons.append('MIN_90_FORWARD_DAYS')
    if int(e.get('rebalances') or e.get('trades') or 0)<12:reasons.append('MIN_12_FORWARD_EVIDENCE_EVENTS')
    if _f(e.get('excess_pct'),-999)<=0:reasons.append('NO_POSITIVE_BENCHMARK_EXCESS')
    if _f(e.get('max_drawdown_pct'),999)>8:reasons.append('MAX_DRAWDOWN_ABOVE_8')
    if e.get('lineage_status')!='PASS':reasons.append('LINEAGE_INTEGRITY_NOT_PASS')
    if e.get('reproducible') is not True:reasons.append('REPRODUCIBILITY_NOT_PASS')
    rows=(candidate or {}).get('rows') or []
    if len(rows)<10:reasons.append('INSUFFICIENT_RANKED_UNIVERSE')
    if not candidate.get('as_of'):reasons.append('AS_OF_MISSING')
    return {'status':'ELIGIBLE' if not reasons else 'OBSERVE','reasons':reasons}

def _rank_pct(rows,common):
    vals=[]
    for x in rows:
        t=str(x.get('ticker') or '').upper().replace('.IS','')
        if t in common and isinstance(x.get('score'),(int,float)):vals.append((t,float(x['score'])))
    vals.sort(key=lambda x:(x[1],x[0]))
    n=len(vals)
    return {t:(i/(n-1) if n>1 else .5) for i,(t,_) in enumerate(vals)}

def _weights(candidates,max_weight=.40):
    quality=[]
    for c in candidates:
        e=c.get('forward_evidence') or {}
        q=max(.01,_f(e.get('excess_pct'),0)-.35*max(0,_f(e.get('max_drawdown_pct'),0)))
        quality.append(q)
    a=np.asarray(quality,float);a=a/a.sum()
    cap=max(.34,min(float(max_weight),.50))
    for _ in range(20):
        over=a>cap
        if not np.any(over):break
        excess=float((a[over]-cap).sum());a[over]=cap
        under=~over
        if not np.any(under):break
        room=np.maximum(cap-a[under],0);rs=float(room.sum())
        if rs<=1e-12:break
        a[under]+=room/rs*excess
    a=a/a.sum()
    return a

def build(candidates,max_model_weight=.40):
    raw=list(candidates or [])
    checked=[{**c,'evidence_gate':evidence_gate(c)} for c in raw]
    eligible=[c for c in checked if c['evidence_gate']['status']=='ELIGIBLE']
    if len(eligible)<3:
        return {'status':'INSUFFICIENT_DIVERSITY','eligible_models':len(eligible),'candidates':checked,
                'promotion_status':'RESEARCH_ONLY','live_execution':False}
    dates={str(c.get('as_of')) for c in eligible}
    if len(dates)!=1:
        return {'status':'AS_OF_MISMATCH','as_of_values':sorted(dates),'promotion_status':'RESEARCH_ONLY','live_execution':False}
    ticker_sets=[{str(x.get('ticker') or '').upper().replace('.IS','') for x in (c.get('rows') or []) if x.get('ticker')} for c in eligible]
    common=set.intersection(*ticker_sets) if ticker_sets else set()
    if len(common)<10:
        return {'status':'INSUFFICIENT_COMMON_UNIVERSE','common_symbols':len(common),
                'promotion_status':'RESEARCH_ONLY','live_execution':False}
    weights=_weights(eligible,max_model_weight)
    ranks=[_rank_pct(c.get('rows') or [],common) for c in eligible]
    pairwise=[]
    for i in range(len(ranks)):
        for j in range(i+1,len(ranks)):
            a=np.asarray([ranks[i][t] for t in sorted(common)],float)
            b=np.asarray([ranks[j][t] for t in sorted(common)],float)
            corr=float(np.corrcoef(a,b)[0,1]) if np.std(a)>0 and np.std(b)>0 else 1.0
            pairwise.append({'a':eligible[i].get('id'),'b':eligible[j].get('id'),'rank_corr':round(corr,4)})
    mean_corr=float(np.mean([x['rank_corr'] for x in pairwise])) if pairwise else 1.0
    flags=[]
    if mean_corr>.95:flags.append('HIGH_MODEL_REDUNDANCY')
    rows=[]
    for t in sorted(common):
        score=sum(float(weights[i])*ranks[i][t] for i in range(len(eligible)))
        rows.append({'ticker':t,'score':round(score,6),
                     'constituent_rank_scores':{str(eligible[i].get('id')):round(ranks[i][t],6) for i in range(len(eligible))}})
    rows.sort(key=lambda x:(-x['score'],x['ticker']))
    components=[{'id':c.get('id'),'name':c.get('name'),'weight':round(float(weights[i]),6),
                 'model_fingerprint':c.get('model_fingerprint'),'forward_evidence':c.get('forward_evidence')}
                for i,c in enumerate(eligible)]
    artifact=register_artifact({
        'model_name':'BIST Forward-Evidence Ensemble Challenger','model_version':'74.0','seed':74,
        'features':['constituent_rank_percentiles'],'label':'relative_rank_score','train_rows':None,'train_dates':None,
        'train_cutoff':None,'as_of':next(iter(dates)),'symbols':len(common),
        'params':{'components':components,'max_model_weight':max_model_weight,'mean_pairwise_rank_corr':mean_corr}
    })
    return {'status':'CAUTION' if flags else 'OK','flags':flags,'as_of':next(iter(dates)),
            'common_symbols':len(common),'components':components,'pairwise_rank_correlations':pairwise,
            'mean_pairwise_rank_corr':round(mean_corr,4),'rows':rows,'model_artifact':artifact,
            'promotion_status':'RESEARCH_ONLY','paper_execution_enabled':False,'live_execution':False,
            'policy':'Only mature prospective candidates are combined. Ensemble output remains research-only and must earn its own forward paper evidence.'}
