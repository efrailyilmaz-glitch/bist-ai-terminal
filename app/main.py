from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .universe import get_universe
from .market_data import scan_codes, yahoo_chart, market_overview, multi_timeframe
from .backtest import run_backtest

BASE=Path(__file__).resolve().parent
app=FastAPI(title='BIST AI Terminal',version='3.2')
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
def backtest(ticker:str,fast:int=20,slow:int=50,period:str='2y'):
    fast=max(5,min(fast,100)); slow=max(fast+5,min(slow,250))
    return run_backtest(ticker,fast=fast,slow=slow,period=period)

@app.get('/api/market')
def market(): return market_overview()

@app.get('/api/kap')
def kap():
    return {'status':'PUBLIC_SOURCE_READY','source':'KAP','url':'https://www.kap.org.tr/tr/bildirim-sorgu',
            'message':'KAP bildirim/NLP katmanı V3 veri motoruna ayrılmıştır. Lisanslı REST veri yayını bağlanana kadar sahte canlı bildirim üretilmez.'}

@app.get('/health')
def health():
    u=get_universe()
    return {'status':'ok','version':'3.2','universe_count':len(u),'universe_source':u[0].get('source') if u else 'NONE'}
