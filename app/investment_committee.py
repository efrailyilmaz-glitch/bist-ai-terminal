from __future__ import annotations
import math, time
from .market_data import scan_codes, market_overview, yahoo_rows
from .fundamentals import get_fundamentals
from .analyst_engine import trusted_research
from .premium_engine import fair_value_health
from .alpha_engine import validate_alpha, ensemble_signal
from .opportunity_engine import score_opportunity
from .kap_engine import disclosures
from .news_engine import headlines
from .pro_tools import technical_pro, forensic_models

def _v(x,d=None):
    try:
        if x is None:return d
        v=float(x)
        return d if math.isnan(v) or math.isinf(v) else v
    except Exception:return d

def _cap(x,a=0,b=100):return max(a,min(b,x))

def _current_regime():
    try:
        d=yahoo_rows('XU100',period='2y',interval='1d');rows=d.get('candles') or []
        if len(rows)<220:return 'UNKNOWN'
        c=[float(x['close']) for x in rows]
        import pandas as pd, numpy as np
        s=pd.Series(c);e50=s.ewm(span=50,adjust=False).mean().iloc[-1];e200=s.ewm(span=200,adjust=False).mean().iloc[-1]
        vol=s.pct_change().tail(20).std()*math.sqrt(252)*100
        if s.iloc[-1]>e50>e200:return 'BULL'
        if s.iloc[-1]<e50<e200:return 'BEAR'
        return 'HIGH_VOL_SIDEWAYS' if vol>35 else 'SIDEWAYS'
    except Exception:return 'UNKNOWN'

def _empirical(alpha,regime):
    h20=(alpha.get('horizons') or {}).get('20d') or {}
    rh=((alpha.get('regimes') or {}).get(regime) or {}).get('h20') or {}
    use=rh if (rh.get('n') or 0)>=10 else h20
    p=_v(use.get('hit_rate_pct'),50)/100
    med=_v(use.get('median_excess_pct'),0)
    p10=_v(use.get('p10_excess_pct'),-8)
    p90=_v(use.get('p90_excess_pct'),8)
    return {'sample':use.get('n',0),'hit_probability':round(p,3),'median_excess_pct':med,'p10_excess_pct':p10,'p90_excess_pct':p90,'source':'REGIME' if use is rh else 'ALL'}

def investment_committee(ticker:str,portfolio_value=1_000_000,risk_budget_pct=.75,max_position_pct=12.0):
    code=ticker.upper().replace('.IS','')
    rows=scan_codes([code]);tech=rows[0] if rows else {}
    if not tech:return {'ticker':code,'status':'NO_DATA'}
    price=_v(tech.get('price'),0);fund=get_fundamentals(code);analyst=trusted_research(code,current_price=price,fundamentals=fund)
    premium=fair_value_health(code);protech=technical_pro(code);forensic=forensic_models(code);alpha=validate_alpha(code,period='10y',step=5,min_score=60);ensemble=ensemble_signal(code)
    macro=market_overview();kap=disclosures(code,limit=10);news=headlines(code,limit=12);opp=score_opportunity(tech,fund,analyst,macro,kap,news)
    regime=_current_regime();emp=_empirical(alpha,regime) if alpha.get('status')=='OK' else {'sample':0,'hit_probability':.5,'median_excess_pct':0,'p10_excess_pct':-10,'p90_excess_pct':10,'source':'NONE'}

    gates=[];veto=[]
    def gate(name,passed,detail,hard=False):
        gates.append({'name':name,'pass':bool(passed),'detail':detail,'hard':hard})
        if hard and not passed:veto.append(name)

    liq=_v(tech.get('avg_value_turnover_20'),0);risk=_v(tech.get('risk'),100);anom=_v(tech.get('anomaly_score'),100)
    health=_v(premium.get('health_score'));fv_up=_v(premium.get('fair_value_upside_pct'));piot=(premium.get('piotroski') or {}).get('score');alt=(premium.get('altman') or {}).get('status')
    gate('Likidite',liq>=5_000_000,f'20G ort. işlem değeri ≈ ₺{liq:,.0f}',True)
    gate('Aşırı risk yok',risk<82,f'Risk skoru {risk:.0f}/100',True)
    gate('Manipülasyon/anomali proxy aşırı değil',anom<90,f'Anomali {anom:.0f}/100',True)
    gate('Uzun trend bozuk değil',not (tech.get('supertrend')=='BEARISH' and tech.get('ichimoku')=='BEARISH'),f"{tech.get('supertrend')} / {tech.get('ichimoku')}",True)
    gate('Tarihsel edge örneklemi',emp.get('sample',0)>=15,f"N={emp.get('sample',0)} · {emp.get('source')}",False)
    gate('Tarihsel hit-rate',emp.get('hit_probability',.5)>=.55,f"{emp.get('hit_probability',.5)*100:.1f}%",False)
    gate('Ensemble anlaşması',ensemble.get('agreement')!='LOW',f"{ensemble.get('agreement')} · dispersion {ensemble.get('dispersion')}",False)
    gate('Fundamental sağlık',health is None or health>=50,'Health '+('—' if health is None else f'{health:.0f}/100'),False)
    gate('Değerleme marjı',fv_up is None or fv_up>=5,'Fair value potansiyeli '+('—' if fv_up is None else f'{fv_up:.1f}%'),False)
    gate('Bilanço stres veto',alt!='DISTRESS',f'Altman {alt or "—"}',True)
    if piot is not None:gate('Piotroski',piot>=4,f'{piot}/9',False)
    gate('VWAP/AVWAP teknik teyit',_v(protech.get('alignment_score'),50)>=40,f"Pro teknik teyit {protech.get('alignment_score','—')}/100",False)
    beneish=(forensic.get('beneish') or {})
    gate('Beneish muhasebe riski',beneish.get('status')!='ELEVATED_RISK',f"Beneish {beneish.get('score','—')} · {beneish.get('status','—')}",False)

    target=(opp.get('targets') or {}).get('short_target_1') or (opp.get('targets') or {}).get('medium_target')
    stop=(opp.get('targets') or {}).get('short_stop')
    upside=((target/price)-1)*100 if target and price else None
    downside=((price-stop)/price)*100 if stop and price and stop<price else max(4,_v(tech.get('atr_pct'),3)*1.5)
    rr=(upside/downside) if upside is not None and downside else None
    p=emp.get('hit_probability',.5)
    win=max(0,upside if upside is not None else emp.get('p90_excess_pct',8))
    loss=max(0,downside)
    ev=p*win-(1-p)*loss
    b=(win/loss) if loss>0 else 0
    kelly=max(0,(b*p-(1-p))/b) if b>0 else 0
    quarter_kelly=kelly*.25

    atr=_v(tech.get('atr'),price*.03);risk_budget=max(0,float(portfolio_value))*max(0,float(risk_budget_pct))/100
    unit_risk=max(abs(price-(stop or price-1.5*atr)),price*.005)
    risk_units=(risk_budget/unit_risk) if unit_risk>0 else 0
    risk_position_value=risk_units*price
    liquidity_cap=liq*.05
    pct_cap=max(0,float(portfolio_value))*max(0,float(max_position_pct))/100
    kelly_cap=max(0,float(portfolio_value))*min(.15,quarter_kelly)
    caps=[x for x in [risk_position_value,liquidity_cap,pct_cap,kelly_cap if kelly_cap>0 else pct_cap] if x>0]
    research_position=min(caps) if caps else 0
    position_pct=(research_position/portfolio_value*100) if portfolio_value>0 else 0

    evidence={
      'opportunity':_v(opp.get('opportunity_score'),50),'ensemble':_v(ensemble.get('ensemble_score'),50),
      'alpha':_cap(50+(emp.get('hit_probability',.5)-.5)*120+emp.get('median_excess_pct',0)*2),
      'fundamental':_v(fund.get('fundamental_score'),50),'health':health if health is not None else 50,
      'valuation':_cap(50+(fv_up or 0)*1.2),'analyst':_v(analyst.get('analyst_score'),50),
      'macro':_v(macro.get('global_score'),50),'risk_quality':_cap(100-risk*.7-anom*.3),'pro_technical':_v(protech.get('alignment_score'),50)
    }
    weights={'opportunity':.18,'ensemble':.15,'alpha':.18,'fundamental':.12,'health':.10,'valuation':.08,'analyst':.07,'macro':.05,'risk_quality':.05,'pro_technical':.02}
    composite=round(sum(evidence[k]*weights[k] for k in weights))
    soft_pass=sum(1 for x in gates if x['pass']);gate_ratio=soft_pass/max(1,len(gates))
    composite=round(_cap(composite*(.85+.15*gate_ratio)))
    if veto:decision='NO_TRADE';decision_tr='PAS GEÇ'
    elif composite>=80 and ev>0 and (rr is None or rr>=1.5) and emp.get('sample',0)>=15:decision='PASS';decision_tr='ARAŞTIRMA ONAYI'
    elif composite>=68 and ev>=0:decision='WATCH';decision_tr='İZLE / TEYİT BEKLE'
    else:decision='NO_TRADE';decision_tr='PAS GEÇ'

    scenarios={
      'bear':{'price':round(max(0,price*(1+emp.get('p10_excess_pct',-10)/100)),2),'basis':'historical P10 excess proxy'},
      'base':{'price':round(price*(1+emp.get('median_excess_pct',0)/100),2),'basis':'historical median excess proxy'},
      'bull':{'price':round(price*(1+emp.get('p90_excess_pct',10)/100),2),'basis':'historical P90 excess proxy'}
    }
    invalidation=[]
    if stop:invalidation.append(f'Fiyat ₺{stop:.2f} altında kapanırsa kısa tez bozulur')
    invalidation+=['Supertrend + Ichimoku birlikte bearish olursa','Yeni yüksek materyaliteli negatif KAP olayı oluşursa','Alpha hit-rate yeni örneklerle belirgin biçimde bozulursa']
    return {'ticker':code,'status':'OK','decision':decision,'decision_tr':decision_tr,'committee_score':composite,'regime':regime,
            'expected_value_pct':round(ev,2),'risk_reward':None if rr is None else round(rr,2),'empirical':emp,'evidence':{k:round(v,1) for k,v in evidence.items()},
            'gates':gates,'vetoes':veto,'scenario_map':scenarios,'targets':opp.get('targets'),'position_sizing':{
                'portfolio_value':portfolio_value,'risk_budget_pct':risk_budget_pct,'risk_budget_amount':round(risk_budget,2),
                'quarter_kelly_pct':round(quarter_kelly*100,2),'max_position_pct':max_position_pct,
                'liquidity_cap_5pct_adv':round(liquidity_cap,2),'research_position_value':round(research_position,2),'research_position_pct':round(position_pct,2),
                'note':'Research sizing proxy only; combines stop-distance risk budget, 5% ADV liquidity cap, max-position cap and quarter-Kelly cap.'
            },'invalidation':invalidation,'opportunity':opp,'alpha_validation':alpha,'ensemble':ensemble,'premium':premium,'pro_technical':protech,'forensics':forensic,
            'note':'Committee can veto strong signals. This is a research decision framework, not an instruction to transact.'}
