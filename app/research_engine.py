from __future__ import annotations
import time
from .market_data import scan_codes, market_overview
from .fundamentals import get_fundamentals
from .kap_engine import company_profile, disclosures
from .news_engine import headlines

def _v(x,default=50):
    try:return float(x) if x is not None else float(default)
    except Exception:return float(default)

def _stance(score):
    if score>=78:return 'STRONG_POSITIVE'
    if score>=63:return 'POSITIVE'
    if score>=45:return 'NEUTRAL'
    if score>=30:return 'CAUTIOUS'
    return 'NEGATIVE'

def _kap_signal(d):
    items=d.get('items') or []
    if not items:return 50,None
    weighted=[]
    for x in items:
        s=_v(x.get('sentiment_score'),0)
        m=max(10,_v(x.get('materiality'),25))
        weighted.append((50+s/2,m))
    num=sum(s*w for s,w in weighted);den=sum(w for _,w in weighted)
    return round(num/den,1) if den else 50, max(items,key=lambda x:x.get('materiality',0))

def research_snapshot(ticker:str):
    code=ticker.upper().replace('.IS','')
    tech_rows=scan_codes([code])
    tech=tech_rows[0] if tech_rows else {}
    fund=get_fundamentals(code)
    kap=disclosures(code)
    profile=company_profile(code)
    news=headlines(code)
    macro=market_overview()

    short_tech=_v(tech.get('short_score'))
    long_tech=_v(tech.get('long_score'))
    fundamental=_v(fund.get('fundamental_score'))
    news_score=50+_v(news.get('headline_sentiment'),0)/2
    kap_score,top_event=_kap_signal(kap)
    macro_score=_v(macro.get('global_score'))

    fcoverage=_v(fund.get('coverage_pct'),0)
    fund_weight=.24 if fcoverage>=55 else (.14 if fcoverage>=25 else 0)
    short_weights={'technical':.50,'fundamental':fund_weight,'kap':.10,'news':.08,'macro':.08}
    long_weights={'technical':.30,'fundamental':.44 if fcoverage>=55 else (.25 if fcoverage>=25 else 0),'kap':.10,'news':.05,'macro':.11}

    def combine(weights,technical):
        vals={'technical':technical,'fundamental':fundamental,'kap':kap_score,'news':news_score,'macro':macro_score}
        den=sum(weights[k] for k in weights if k!='fundamental' or weights[k]>0)
        return sum(vals[k]*weights[k] for k in weights)/den if den else 50

    short=combine(short_weights,short_tech)
    long=combine(long_weights,long_tech)

    risk=_v(tech.get('risk'),50)
    anomaly=_v(tech.get('anomaly_score'),0)
    penalty=max(0,(risk-65)*.12)+max(0,(anomaly-70)*.10)
    short=max(0,min(100,short-penalty))
    long=max(0,min(100,long-penalty*.7))

    flags=[]
    if fund.get('debt_to_equity') is not None and fund['debt_to_equity']>2:flags.append('Yüksek borç/özsermaye')
    if fund.get('revenue_growth_pct') is not None and fund['revenue_growth_pct']<-10:flags.append('Gelir büyümesi negatif')
    if fund.get('earnings_growth_pct') is not None and fund['earnings_growth_pct']<-15:flags.append('Kâr büyümesi negatif')
    if tech.get('rsi_divergence')=='BEARISH' or tech.get('macd_divergence')=='BEARISH':flags.append('Bearish divergence')
    if tech.get('supertrend')=='BEARISH' and tech.get('ichimoku')=='BEARISH':flags.append('Trend yapısı negatif')
    if anomaly>=70:flags.append('Yüksek fiyat/hacim anomalisi')
    if fcoverage<25:flags.append('Temel veri kapsamı düşük')

    strengths=[]
    if fund.get('quality_score') is not None and fund['quality_score']>=70:strengths.append('Yüksek kalite faktörü')
    if fund.get('growth_score') is not None and fund['growth_score']>=70:strengths.append('Güçlü büyüme faktörü')
    if fund.get('value_score') is not None and fund['value_score']>=70:strengths.append('Görece cazip değerleme faktörü')
    if tech.get('relative_strength_20',0)>5:strengths.append('XU100 üzerinde relative strength')
    if tech.get('supertrend')=='BULLISH' and tech.get('ichimoku')=='BULLISH':strengths.append('Trend uyumu pozitif')
    if tech.get('rsi_divergence')=='BULLISH' or tech.get('macd_divergence')=='BULLISH':strengths.append('Bullish divergence')
    if top_event and top_event.get('sentiment_score',0)>0:strengths.append('Pozitif KAP olayı')

    component_coverage={
      'technical':100 if tech else 0,'fundamental':fcoverage,
      'kap':100 if kap.get('items') else 0,'news':100 if news.get('items') else 0,'macro':100 if macro.get('mode')!='DATA UNAVAILABLE' else 0
    }
    confidence=round(.35*component_coverage['technical']+.35*component_coverage['fundamental']+.12*component_coverage['kap']+.08*component_coverage['news']+.10*component_coverage['macro'])
    return {
      'ticker':code,'updated':time.strftime('%d.%m.%Y %H:%M:%S'),
      'short_research_score':round(short),'long_research_score':round(long),
      'short_stance':_stance(short),'long_stance':_stance(long),'confidence':confidence,
      'components':{
        'technical_short':round(short_tech),'technical_long':round(long_tech),'fundamental':fund.get('fundamental_score'),
        'kap':round(kap_score),'news':round(news_score),'macro':round(macro_score),'risk':round(risk),'anomaly':round(anomaly)
      },
      'coverage':component_coverage,'strengths':strengths[:6],'flags':flags[:6],
      'technical':tech,'fundamentals':fund,'kap_profile':profile,'kap':kap,'news':news,'macro':macro
    }
