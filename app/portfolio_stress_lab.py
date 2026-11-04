"""V76 deterministic portfolio stress lab for prospective XS paper portfolios.
Stress results are diagnostic/veto-only and never increase exposure or enable live execution.
"""
from __future__ import annotations
import math

def _f(x,default=0.0):
    try:
        z=float(x)
        return z if math.isfinite(z) else default
    except Exception:return default

def _weights(history):
    rows=(history or {}).get('positions') or []
    out=[]
    for r in rows:
        w=max(0.0,_f(r.get('weight')))
        if w>0: out.append({'ticker':str(r.get('ticker') or ''),'weight':w,'sector':r.get('sector')})
    total=sum(x['weight'] for x in out)
    if total>1.000001:
        for x in out:x['weight']/=total
    return out

def evaluate(history,max_review_loss_pct=10.0,max_block_loss_pct=14.0):
    pos=_weights(history)
    if not pos:
        return {'status':'OBSERVE','reasons':['NO_ACTIVE_POSITIONS'],'scenarios':[]}
    invested=min(1.0,sum(x['weight'] for x in pos));cash=max(0.0,1.0-invested)
    ordered=sorted(pos,key=lambda x:x['weight'],reverse=True)
    top_weight=sum(x['weight'] for x in ordered[:min(3,len(ordered))])
    sector_known=[x for x in pos if x.get('sector')]
    sector_weights={}
    for x in sector_known: sector_weights[x['sector']]=sector_weights.get(x['sector'],0)+x['weight']
    max_sector=max(sector_weights.values()) if sector_weights else None

    scenarios=[]
    def add(name,loss,detail):
        scenarios.append({'scenario':name,'loss_pct':round(max(0.0,loss)*100,3),'detail':detail})

    add('MARKET_GAP_DOWN',invested*.085,
        'Broad 8.5% overnight gap-down proxy across invested exposure; cash is unchanged.')
    add('CORRELATION_SPIKE',invested*.105,
        'Diversification collapse proxy: all invested names move together under a 10.5% adverse shock.')
    add('LIQUIDITY_DRY_UP',invested*.045 + min(.02,top_weight*.02),
        'Execution/liquidity haircut proxy under reduced depth and wider realized slippage.')
    add('TOP_CLUSTER_SHOCK',top_weight*.14 + max(0.0,invested-top_weight)*.025,
        'Largest three weights suffer a 14% cluster shock; remaining exposure receives a 2.5% spillover shock.')
    if max_sector is not None:
        add('SECTOR_CLUSTER_SHOCK',max_sector*.15 + max(0.0,invested-max_sector)*.02,
            'Largest known sector sleeve receives a 15% shock with 2% portfolio spillover.')
    else:
        add('SECTOR_CLUSTER_SHOCK',top_weight*.12 + max(0.0,invested-top_weight)*.02,
            'Sector metadata unavailable; conservative top-weight cluster proxy is used instead.')

    worst=max(scenarios,key=lambda x:x['loss_pct'])
    reasons=[]
    if max_sector is None: reasons.append('SECTOR_METADATA_UNKNOWN')
    if worst['loss_pct']>float(max_block_loss_pct): reasons.append('EXTREME_STRESS_LOSS')
    elif worst['loss_pct']>float(max_review_loss_pct): reasons.append('STRESS_LOSS_ABOVE_REVIEW_LIMIT')
    if top_weight>.50: reasons.append('TOP3_CONCENTRATION_HIGH')
    status='BLOCK' if 'EXTREME_STRESS_LOSS' in reasons else ('OBSERVE' if any(x!='SECTOR_METADATA_UNKNOWN' for x in reasons) else 'PASS')
    # Unknown sector metadata alone is transparent caution, not an automatic veto.
    if reasons==['SECTOR_METADATA_UNKNOWN']: status='PASS'
    return {'status':status,'reasons':reasons,'invested_weight_pct':round(invested*100,2),
            'cash_weight_pct':round(cash*100,2),'top3_weight_pct':round(top_weight*100,2),
            'max_known_sector_weight_pct':None if max_sector is None else round(max_sector*100,2),
            'worst_scenario':worst,'scenarios':scenarios,
            'policy':'Deterministic paper stress only. Results can veto promotion review; they never increase exposure or authorize live execution.'}
