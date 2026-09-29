from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path
from .universe import get_universe
from .market_data import scan_codes, yahoo_chart, market_overview, multi_timeframe
from .backtest import run_backtest, compare_strategies, walk_forward, monte_carlo
from .fundamentals import get_fundamentals, factor_screen
from .kap_engine import company_profile, disclosures
from .news_engine import headlines
from .research_engine import research_snapshot
from .providers import data_health, provider_registry
from .market_internals import market_internals
from .catalysts import catalyst_calendar
from .model_governance import model_card
from .portfolio_analytics import analyze_portfolio, compare_allocations, optimize_alpha_portfolio
from .analyst_engine import trusted_research
from .opportunity_engine import start_radar, trigger_refresh, radar_snapshot, alerts_snapshot
from .premium_engine import fair_value_health, volume_profile
from .alpha_engine import validate_alpha, ensemble_signal, sector_rotation, event_study
from .institutional_connectors import institutional_provider_status
from .investment_committee import investment_committee
from .pro_tools import technical_pro, forensic_models, peer_comparison, compare_symbols
from .pro_alert_engine import start_alert_engine, add_rule, delete_rule, list_rules, events as pro_alert_events, evaluate_once as evaluate_pro_alerts

BASE=Path(__file__).resolve().parent
app=FastAPI(title='BIST AI Terminal',version='10.0')
app.add_middleware(GZipMiddleware,minimum_size=800)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='SAMEORIGIN'
        response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        return response

app.add_middleware(SecurityHeadersMiddleware)
app.mount('/static',StaticFiles(directory=str(BASE/'static')),name='static')

@app.get('/',response_class=HTMLResponse)
def index(): return (BASE/'templates/index.html').read_text(encoding='utf-8')

@app.get('/api/universe')
def universe(force: bool=False):
    rows=get_universe(force=force)
    return {'count':len(rows),'source':rows[0].get('source','UNKNOWN') if rows else 'NONE','rows':rows}

@app.get('/api/scan')
def scan(offset:int=0,limit:int=60,codes:str|None=None):
    universe=get_universe()
    if codes:
        chosen=[x.strip().upper() for x in codes.split(',') if x.strip()][:100]
    else:
        chosen=[x['ticker'] for x in universe[offset:offset+max(1,min(limit,100))]]
    data=scan_codes(chosen)
    names={x['ticker']:x for x in universe}
    for row in data:
        meta=names.get(row['ticker'],{})
        row['name']=meta.get('name',row['ticker']); row['city']=meta.get('city','')
    return {'total':len(universe),'offset':offset,'requested':len(chosen),'received':len(data),'rows':data}

@app.get('/api/chart/{ticker}')
def chart(ticker:str, period:str='1y', interval:str='1d'):
    return yahoo_chart(ticker,period=period,interval=interval)

@app.get('/api/mtf/{ticker}')
def mtf(ticker:str):
    return multi_timeframe(ticker)

@app.get('/api/backtest/{ticker}')
def backtest(ticker:str,fast:int=20,slow:int=50,period:str='5y',strategy:str='ma_trend',cost_bps:int=10,slippage_bps:int=5):
    fast=max(5,min(fast,100)); slow=max(fast+5,min(slow,250))
    return run_backtest(ticker,fast=fast,slow=slow,period=period,strategy=strategy,
                        cost_bps=max(0,min(cost_bps,100)),slippage_bps=max(0,min(slippage_bps,100)))

@app.get('/api/strategy-compare/{ticker}')
def strategy_compare(ticker:str,period:str='5y',cost_bps:int=10,slippage_bps:int=5):
    return compare_strategies(ticker,period=period,cost_bps=max(0,min(cost_bps,100)),slippage_bps=max(0,min(slippage_bps,100)))

@app.get('/api/walk-forward/{ticker}')
def walkforward(ticker:str,period:str='5y',strategy:str='ma_trend',cost_bps:int=10,slippage_bps:int=5):
    return walk_forward(ticker,period=period,strategy=strategy,cost_bps=max(0,min(cost_bps,100)),slippage_bps=max(0,min(slippage_bps,100)))

@app.get('/api/monte-carlo/{ticker}')
def montecarlo(ticker:str,period:str='5y',strategy:str='ma_trend',fast:int=20,slow:int=50,cost_bps:int=10,slippage_bps:int=5):
    return monte_carlo(ticker,period=period,strategy=strategy,fast=fast,slow=slow,
                       cost_bps=max(0,min(cost_bps,100)),slippage_bps=max(0,min(slippage_bps,100)))

@app.get('/api/fundamentals/{ticker}')
def fundamentals(ticker:str,force:bool=False):
    return get_fundamentals(ticker,force=force)

@app.get('/api/factor-screen')
def factors(codes:str):
    selected=[x.strip().upper() for x in codes.split(',') if x.strip()][:24]
    return factor_screen(selected)

@app.get('/api/kap-profile/{ticker}')
def kap_profile(ticker:str,force:bool=False):
    return company_profile(ticker,force=force)

@app.get('/api/kap-disclosures/{ticker}')
def kap_disclosures(ticker:str,limit:int=12):
    return disclosures(ticker,limit=max(1,min(limit,30)))

@app.get('/api/news/{ticker}')
def news(ticker:str,limit:int=15):
    data=headlines(ticker,limit=max(1,min(limit,30)))
    return data

@app.get('/api/research/{ticker}')
def research(ticker:str):
    return research_snapshot(ticker)

@app.get('/api/analysts/{ticker}')
def analysts(ticker:str):
    f=get_fundamentals(ticker)
    return trusted_research(ticker,current_price=f.get('current_price'),fundamentals=f)

@app.get('/api/premium/{ticker}')
def premium(ticker:str):
    return fair_value_health(ticker)

@app.get('/api/volume-profile/{ticker}')
def volumeprofile(ticker:str,period:str='6mo',interval:str='1d',bins:int=28):
    return volume_profile(ticker,period=period,interval=interval,bins=bins)

@app.get('/api/alpha-validation/{ticker}')
def alpha_validation(ticker:str,period:str='10y',step:int=5,min_score:int=60):
    return validate_alpha(ticker,period=period,step=max(1,min(step,20)),min_score=max(50,min(min_score,95)))

@app.get('/api/ensemble/{ticker}')
def ensemble(ticker:str):
    return ensemble_signal(ticker)

@app.get('/api/sector-rotation')
def sectorrotation(limit:int=40):
    return sector_rotation(limit=limit)

@app.get('/api/event-study/{ticker}')
def eventstudy(ticker:str,limit:int=25):
    return event_study(ticker,limit=max(5,min(limit,40)))

@app.get('/api/committee/{ticker}')
def committee(ticker:str,portfolio_value:float=1000000,risk_budget_pct:float=.75,max_position_pct:float=12.0):
    return investment_committee(ticker,portfolio_value=max(0,portfolio_value),risk_budget_pct=max(.05,min(risk_budget_pct,5)),max_position_pct=max(1,min(max_position_pct,50)))

@app.get('/api/pro-technical/{ticker}')
def pro_technical(ticker:str):
    return technical_pro(ticker)

@app.get('/api/forensics/{ticker}')
def forensics(ticker:str):
    return forensic_models(ticker)

@app.get('/api/peers/{ticker}')
def peers(ticker:str,peer_count:int=5):
    return peer_comparison(ticker,peer_count=max(3,min(peer_count,8)))

@app.get('/api/compare')
def compare(codes:str):
    return compare_symbols([x.strip() for x in codes.split(',') if x.strip()])

@app.get('/api/export/chart/{ticker}')
def export_chart(ticker:str,period:str='2y',interval:str='1d'):
    from .market_data import yahoo_rows
    import csv, io
    rows=yahoo_rows(ticker,period=period,interval=interval).get('candles') or []
    s=io.StringIO();w=csv.DictWriter(s,fieldnames=['time','open','high','low','close','volume']);w.writeheader()
    for x in rows:w.writerow({k:x.get(k) for k in w.fieldnames})
    return Response(content=s.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename={ticker.upper()}_{interval}.csv'})

@app.get('/api/export/fundamentals/{ticker}')
def export_fundamentals(ticker:str):
    import csv, io
    f=get_fundamentals(ticker);s=io.StringIO();w=csv.writer(s);w.writerow(['metric','value'])
    for k,v in sorted(f.items()):
        if isinstance(v,(str,int,float,bool)) or v is None:w.writerow([k,v])
    return Response(content=s.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename={ticker.upper()}_fundamentals.csv'})

@app.get('/api/pro-alert-rules')
def pro_alert_rules():
    return list_rules()

@app.post('/api/pro-alert-rules')
def pro_alert_create(payload:dict=Body(...)):
    try:return add_rule(payload)
    except ValueError as e:return {'error':str(e)}

@app.delete('/api/pro-alert-rules/{rule_id}')
def pro_alert_delete(rule_id:str):
    return delete_rule(rule_id)

@app.get('/api/pro-alert-events')
def pro_alert_events_api(limit:int=100,since:int=0):
    return pro_alert_events(limit=limit,since=since)

@app.post('/api/pro-alert-evaluate')
def pro_alert_evaluate():
    return evaluate_pro_alerts()

@app.get('/api/institutional-providers')
def institutional_providers():
    return institutional_provider_status()

@app.get('/api/opportunities')
def opportunities(limit:int=60):
    return radar_snapshot(limit=limit)

@app.get('/api/alerts')
def alerts(limit:int=50,since:int=0):
    return alerts_snapshot(limit=limit,since=since)

@app.post('/api/radar/refresh')
def radar_refresh():
    return trigger_refresh()

@app.get('/api/portfolio-risk')
def portfolio_risk(codes:str,method:str='equal'):
    selected=[x.strip().upper() for x in codes.split(',') if x.strip()][:12]
    return analyze_portfolio(selected,method=method)

@app.get('/api/portfolio-optimize')
def portfolio_optimize(codes:str,risk_aversion:float=5.0,turnover_penalty:float=.8,max_weight:float=.30):
    selected=[x.strip().upper() for x in codes.split(',') if x.strip()][:12]
    return optimize_alpha_portfolio(selected,risk_aversion=max(.1,min(risk_aversion,20)),turnover_penalty=max(0,min(turnover_penalty,5)),max_weight=max(.10,min(max_weight,.60)))

@app.get('/api/portfolio-allocations')
def portfolio_allocations(codes:str):
    selected=[x.strip().upper() for x in codes.split(',') if x.strip()][:12]
    return compare_allocations(selected)

@app.get('/api/model-card')
def modelcard():
    return model_card()

@app.get('/api/data-health')
def health_data():
    return data_health()

@app.get('/api/providers')
def providers():
    return provider_registry()

@app.get('/api/market-internals')
def internals(codes:str):
    selected=[x.strip().upper() for x in codes.split(',') if x.strip()][:100]
    return market_internals(selected)

@app.get('/api/catalysts')
def catalysts(codes:str):
    selected=[x.strip().upper() for x in codes.split(',') if x.strip()][:16]
    return catalyst_calendar(selected)

@app.get('/api/market')
def market(): return market_overview()

@app.get('/api/kap')
def kap():
    return {'status':'PUBLIC_SOURCE_READY','source':'KAP','url':'https://www.kap.org.tr/tr/bildirim-sorgu',
            'message':'KAP public profile/search katmanı aktiftir. Lisanslı REST veri yayını bağlanana kadar sahte eşzamanlı bildirim üretilmez.'}

@app.on_event('startup')
def desktop_background_radar():
    import os
    if os.getenv('BIST_AI_DESKTOP')=='1':
        start_radar(); start_alert_engine()

@app.get('/health')
def health():
    return {'status':'ok','version':'10.0','service':'bist-ai-terminal'}
