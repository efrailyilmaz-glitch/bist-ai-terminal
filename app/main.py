from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .data_provider import snapshot, market_overview, kap_feed, portfolio, backtest

BASE=Path(__file__).resolve().parent
app=FastAPI(title="BIST AI Terminal",version="2.0")
app.mount("/static",StaticFiles(directory=str(BASE/"static")),name="static")

@app.get("/",response_class=HTMLResponse)
def index(): return (BASE/"templates/index.html").read_text(encoding="utf-8")
@app.get("/api/market")
def api_market(): return market_overview()
@app.get("/api/stocks")
def api_stocks(): return snapshot()
@app.get("/api/stocks/{ticker}")
def api_stock(ticker:str):
    t=ticker.upper().replace(".IS","")
    return next((x for x in snapshot() if x["ticker"]==t),{"error":"not_found"})
@app.get("/api/kap")
def api_kap(): return kap_feed()
@app.get("/api/portfolio")
def api_portfolio(): return portfolio()
@app.get("/api/backtest")
def api_backtest(): return backtest()
@app.get("/health")
def health(): return {"status":"ok","version":"2.0"}
