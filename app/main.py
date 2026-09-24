from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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
from .portfolio_analytics import analyze_portfolio, compare_allocations

BASE=Path(__file__).resolve().parent
app=FastAPI(title='BIST AI Terminal',version='5.0')
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

@app.get('/api/portfolio-risk')
def portfolio_risk(codes:str,method:str='equal'):
    selected=[x.strip().upper() for x in codes.split(',') if x.strip()][:12]
    return analyze_portfolio(selected,method=method)

@app.get('/api/portfolio-allocations')
def portfolio_allocations(codes:str):
    selected=[x.strip().upper() for x in codes.split(',') if x.strip()][:12]
    return compare_allocations(selected)

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
            'message':'KAP bildirim/NLP katmanı V3 veri motoruna ayrılmıştır. Lisanslı REST veri yayını bağlanana kadar sahte canlı bildirim üretilmez.'}

@app.get('/health')
def health():
    u=get_universe()
    return {'status':'ok','version':'5.0','universe_count':len(u),'universe_source':u[0].get('source') if u else 'NONE'}
