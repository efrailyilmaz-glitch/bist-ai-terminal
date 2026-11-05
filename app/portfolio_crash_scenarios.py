"""V103 portfolio crash/stress scenarios for user-selected research portfolios.
Uses observable portfolio beta, CVaR, concentration and sector weights.
FX/rate scenarios are explicit proxies because issuer-level currency and duration sensitivities are not fully available.
"""
from __future__ import annotations
from .portfolio_decision_intelligence import analyze as portfolio_intelligence

def stress(codes,method='equal'):
    p=portfolio_intelligence(codes,candidate=None,method=method)
    if p.get('status')!='OK':return {'status':p.get('status'),'portfolio':p}
    a=p.get('portfolio') or {};risks=a.get('risk_rows') or [];sectors=p.get('sectors') or []
    beta=sum((float(x.get('beta_xu100') if x.get('beta_xu100') is not None else 1.0)*float(x.get('weight_pct') or 0)/100) for x in risks)
    max_sector=float(sectors[0].get('weight_pct') or 0)/100 if sectors else 0.0
    cvar=abs(float(a.get('cvar95_daily_pct') or 0))
    vol=float(a.get('annual_volatility_pct') or 0)
    avg_corr=float(a.get('avg_correlation') or 0)
    scenarios=[]
    def add(name,loss,detail,quality='MODELLED'):
        scenarios.append({'scenario':name,'loss_pct':round(max(0.0,float(loss)),2),'quality':quality,'detail':detail})
    add('BIST_MINUS_10',abs(beta)*10,'Portfolio beta weighted BIST -10% shock.')
    add('BIST_MINUS_15',abs(beta)*15,'Portfolio beta weighted BIST -15% shock.')
    add('CORRELATION_SPIKE',max(8.0,10.0+max(0,avg_corr-.40)*12),'Diversification collapse proxy using current average correlation.')
    add('LIQUIDITY_DRY_UP',max(4.0,cvar*2.2),'CVaR-based wider-spread / poor-fill proxy; not a live fill forecast.')
    add('SECTOR_CLUSTER_SHOCK',max_sector*18+(1-max_sector)*3,'Largest sector sleeve -18%, remainder -3% spillover.' if sectors else 'Sector metadata unavailable; conservative generic proxy.','MODELLED' if sectors else 'PROXY')
    add('RATE_SHOCK_PROXY',max(5.0,cvar*2.5+max(0,abs(beta)-1)*3),'Macro rate-shock proxy from tail loss and beta; issuer duration sensitivity is not available.','PROXY')
    add('FX_SHOCK_PROXY',max(4.0,cvar*2.0+vol/20),'FX-volatility proxy only; issuer net FX asset/debt exposure is not fully available.','PROXY')
    add('VOLATILITY_REGIME_BREAK',max(6.0,cvar*3.0),'Three-CVaR tail proxy for a volatility regime break.','PROXY')
    scenarios.sort(key=lambda x:-x['loss_pct'])
    worst=scenarios[0] if scenarios else None
    status='BLOCK' if worst and worst['loss_pct']>=18 else 'CAUTION' if worst and worst['loss_pct']>=12 else 'CLEAR'
    return {'status':'OK','version':'103.0','risk_status':status,'portfolio_flags':p.get('flags') or [],
            'metrics':{'portfolio_beta':round(beta,3),'cvar95_daily_pct':round(cvar,3),'annual_volatility_pct':round(vol,2),
                       'avg_correlation':round(avg_corr,3),'max_sector_weight_pct':round(max_sector*100,2)},
            'worst_scenario':worst,'scenarios':scenarios,'live_execution':False,
            'policy':'Stress scenarios are deterministic research diagnostics. Proxy scenarios are explicitly labelled and can only reduce risk appetite; they never increase exposure or authorize execution.'}
