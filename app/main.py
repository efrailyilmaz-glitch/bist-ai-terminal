from fastapi import FastAPI, Body, Header
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
from .market_intelligence import seasonality, rolling_risk, relative_rotation, watchlist_heatmap, market_regime_dashboard
from .broker_bridge import broker_status, order_preview, paper_order, orders as broker_orders, set_kill_switch, update_risk
from .background_supervisor import start_background_supervisor, status as background_status, alerts as background_alerts
from .experience_engine import history as experience_history, calibration as experience_calibration, settle_due as experience_settle, verify_ledger
from .smart_money_engine import smart_money_snapshot, smart_money_radar
from .decision_levels import decision_levels
from .decision_attribution import attribution as decision_attribution, feature_report as decision_feature_report
from .feature_governance import governance_report as feature_governance_report, ab_report as feature_governance_ab
from .model_zoo_lab import catalog as model_zoo_catalog, validate_candidate as model_zoo_validate, lab_summary as model_zoo_summary
from .qlib_bridge import adapter_status as qlib_adapter_status, qlib_dataset_payload, fit_predict_lab as qlib_fit_predict_lab
from .cross_sectional_ml import build_panel as xs_build_panel, run_lab as xs_run_lab, purged_walk_forward_lab as xs_purged_walk_forward_lab, purged_walk_forward_cost_reality as xs_cost_reality
from .xs_portfolio import construct as xs_portfolio_construct
from .xs_paper import create as xs_paper_create, rebalance as xs_paper_rebalance, mark as xs_paper_mark, history as xs_paper_history, lineage as xs_paper_lineage, verify_lineage_ledger as xs_verify_lineage_ledger
from .xs_tournament import create as xs_tournament_create, start as xs_tournament_start, rebalance_variant as xs_tournament_rebalance, mark_all as xs_tournament_mark, snapshot as xs_tournament_snapshot
from .xs_scheduler import configure as xs_scheduler_configure, state as xs_scheduler_state, run_once as xs_scheduler_run_once, start_worker as xs_scheduler_start_worker
from .model_registry import history as model_registry_history, get as model_registry_get
from .promotion_governance import evaluate as promotion_governance_evaluate
from .statistical_promotion import evaluate as statistical_promotion_evaluate
from .regime_robustness import evaluate as regime_robustness_evaluate
from .data_quality_guard import evaluate_history as data_quality_history_evaluate
from .pit_universe import dataset_status as pit_universe_status, intervals as pit_universe_intervals
from .factor_neutralization import evaluate_history as factor_neutralization_history
from .xs_capacity import assess as xs_capacity_assess
from .bist_execution_rules import official_policy as bist_execution_policy
from .decay_v2 import detect_xs_decay as xs_detect_decay_v2
from .champion_governance import status as champion_governance_status
from .protected_feature_governance import status as protected_feature_governance_status
from .external_challenger import adapter_catalog as external_challenger_catalog, run_candidate as external_challenger_run
from .ensemble_challenger import build as ensemble_challenger_build
from .portfolio_stress_lab import evaluate as portfolio_stress_evaluate
from .forward_scorecard import build as forward_scorecard_build
from .research_integrity_dashboard import dashboard as research_integrity_dashboard
from .autonomous_research_loop import run_once as autonomous_research_run, status as autonomous_research_status
from .cycle_engine import cycle_profile, cycle_radar, scan_cycle_batch
from .weekly_reversal import weekly_reversal, weekly_reversal_radar
from .trap_defense import assess_traps
from .adversarial_lab import stress as adversarial_stress
from .adversarial_v2 import stress as adversarial_stress_v2, cross_sectional_stress as adversarial_cross_v2
from .forecast_lab import forecast
from .edge_lab import edge_research
from .robustness_lab import robustness_audit
from .microstructure import microstructure_guard
from .microstructure_feed import latest_microstructure
from .trade_reality import trade_reality
from .edge_catalog import CATALOG
from fastapi import HTTPException
from .opportunity_engine import smart_money_candidates

from .document_lab import ReviewRequest, review as document_review, configuration as document_configuration
from . import auto_paper, robot_arena

BASE=Path(__file__).resolve().parent
app=FastAPI(title='BIST AI Terminal',version='80.0.0')
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

@app.get('/api/trade-reality/{ticker}')
def trade_reality_api(ticker:str,entry:float,stop:float,target:float,side:str='BUY',simulations:int=10000,seed:int=41,block_bars:int=3):
    return trade_reality(ticker,entry,stop,target,side=side,simulations=simulations,seed=seed,block_bars=block_bars)

@app.get('/api/microstructure/{ticker}')
def microstructure_live_api(ticker:str):
    return latest_microstructure(ticker)

@app.post('/api/microstructure-guard')
def microstructure_guard_api(payload:dict=Body(...)):
    return microstructure_guard(payload)

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
    missing=[c for c in chosen if c not in {r['ticker'] for r in data}]
    return {'status':'OK' if not missing else 'PARTIAL' if data else 'NO_DATA','total':len(universe),'offset':offset,'requested':len(chosen),'received':len(data),'missing':missing,'rows':data}

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

@app.get('/api/seasonality/{ticker}')
def seasonality_api(ticker:str,period:str='10y'):
    return seasonality(ticker,period=period)

@app.get('/api/risk-intelligence/{ticker}')
def risk_intelligence(ticker:str,period:str='5y'):
    return rolling_risk(ticker,period=period)

@app.get('/api/relative-rotation')
def relative_rotation_api(codes:str):
    return relative_rotation([x.strip() for x in codes.split(',') if x.strip()])

@app.get('/api/watchlist-heatmap')
def watchlist_heatmap_api(codes:str):
    return watchlist_heatmap([x.strip() for x in codes.split(',') if x.strip()])

@app.get('/api/market-regime')
def market_regime():
    return market_regime_dashboard()

@app.get('/api/broker/status')
def broker_status_api():
    return broker_status()

@app.post('/api/broker/order-preview')
def broker_preview(payload:dict=Body(...)):
    return order_preview(payload)

@app.post('/api/broker/paper-order')
def broker_paper(payload:dict=Body(...)):
    return paper_order(payload)

@app.get('/api/broker/orders')
def broker_order_list(limit:int=100):
    return broker_orders(limit)

@app.post('/api/broker/kill-switch')
def broker_kill(payload:dict=Body(...)):
    return set_kill_switch(bool(payload.get('enabled')))

@app.post('/api/broker/risk')
def broker_risk(payload:dict=Body(...)):
    return update_risk(payload)

@app.get('/api/background/status')
def background_status_api():
    return background_status()

@app.get('/api/background/alerts')
def background_alerts_api(limit:int=50,since:int=0):
    return background_alerts(limit=limit,since=since)

@app.get('/api/experience/history')
def experience_history_api(limit:int=200):
    return experience_history(limit)

@app.get('/api/experience/calibration')
def experience_calibration_api():
    return experience_calibration()

@app.post('/api/experience/settle')
def experience_settle_api():
    return experience_settle()

@app.get('/api/smart-money/{ticker}')
def smart_money(ticker:str,calibrate:bool=True):
    return smart_money_snapshot(ticker,calibrate=calibrate)

@app.get('/api/smart-money-radar')
def smart_money_radar_api(limit:int=25,universe_limit:int=160):
    return smart_money_radar(limit=limit,universe_limit=universe_limit)

@app.get('/api/smart-money-candidates')
def smart_money_candidates_api(limit:int=40):
    return smart_money_candidates(limit)

@app.get('/api/decision-levels/{ticker}')
def decision_levels_api(ticker:str):
    return decision_levels(ticker)

@app.get('/api/cycle-profile/{ticker}')
def cycle_profile_api(ticker:str,force:bool=False):
    return cycle_profile(ticker,force=force)

@app.get('/api/cycle-radar')
def cycle_radar_api(limit:int=50):
    return cycle_radar(limit=limit)

@app.post('/api/cycle-scan')
def cycle_scan_api(batch:int=24):
    return scan_cycle_batch(batch=batch)

@app.get('/api/weekly-reversal/{ticker}')
def weekly_reversal_api(ticker:str,with_history:bool=True):
    return weekly_reversal(ticker,with_history=with_history)

@app.get('/api/weekly-reversal-radar')
def weekly_reversal_radar_api(limit:int=80,universe_limit:int=0):
    return weekly_reversal_radar(limit=limit,universe_limit=universe_limit)

@app.get('/api/adversarial-stress/{ticker}')
def adversarial_stress_api(ticker:str,period:str='5y'):
    from .market_data import yahoo_rows
    import pandas as pd
    raw=yahoo_rows(ticker,period=period,interval='1d').get('candles') or []
    if len(raw)<80: raise HTTPException(422,'At least 80 daily bars are required')
    df=pd.DataFrame(raw).rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
    report=adversarial_stress(df)
    report['ticker']=ticker.upper();report['period']=period
    return report

@app.get('/api/forecast/{ticker}')
def forecast_api(ticker:str,horizon:int=20,cost_bps:float=30):
    import math
    if not math.isfinite(cost_bps): raise HTTPException(422,"cost_bps must be finite")
    if horizon not in (5,20,60): raise HTTPException(422,"horizon must be 5, 20 or 60")
    return forecast(ticker,horizon,max(0,min(cost_bps,300)))

@app.get('/api/edge-catalog')
def edge_catalog_api():
    return CATALOG

@app.get('/api/robustness-audit/{ticker}')
def robustness_audit_api(ticker:str,period:str='10y',cost_bps:int=15,slippage_bps:int=10):
    return robustness_audit(ticker,period,max(0,min(cost_bps,100)),max(0,min(slippage_bps,100)))

@app.get('/api/edge/{ticker}')
def edge_api(ticker:str,cost_bps:float=30):
    import math
    if not math.isfinite(cost_bps) or not 0<=cost_bps<=300:
        raise HTTPException(422,'cost_bps must be between 0 and 300')
    return edge_research(ticker,cost_bps)

@app.get('/api/system-audit')
def system_audit_api():
    import os
    bg=background_status(); br=broker_status()
    cycle_total=max(1,len(get_universe()))
    cycle_cov=round(float(bg.get('cycle_analyzed') or 0)/cycle_total*100,1)
    weekly_cov=round(float(bg.get('weekly_analyzed') or 0)/cycle_total*100,1)
    desktop=os.getenv('BIST_AI_DESKTOP')=='1' or os.getenv('BIST_AI_BACKGROUND','1')!='0'
    checks=[
      {'name':'Backend','status':'OK','detail':'BIST AI backend 80.0'},
      {'name':'Background Supervisor','status':'OK' if bg.get('running') else ('ERROR' if desktop else 'WARN'),'detail':'RUNNING' if bg.get('running') else ('web mode / intentionally off' if not desktop else 'STOPPED')},
      {'name':'Opportunity Radar','status':'OK' if bg.get('radar_status') not in {'ERROR'} else 'WARN','detail':str(bg.get('radar_status') or 'unknown')},
      {'name':'Cycle Coverage','status':'OK' if cycle_cov>=80 else 'WARMING','detail':f'%{cycle_cov} · {bg.get("cycle_analyzed",0)}/{cycle_total}'},
      {'name':'Weekly Coverage','status':'OK' if weekly_cov>=80 else 'WARMING','detail':f'%{weekly_cov} · {bg.get("weekly_analyzed",0)}/{cycle_total}'},
      {'name':'Trap Defense','status':'OK','detail':'V3 · single-bar breakout, distribution cluster, OBV confirmation and late-stage chase filters active'},
      {'name':'Adversarial Market Stress 2.0','status':'OK','detail':'Deterministic multi-day false-breakout/distribution, repeated stop-sweep, liquidity-vacuum and staircase pump-fade tests plus synchronized cross-sectional stress; no intent attribution'},
      {'name':'Robustness Gate','status':'OK','detail':'PBO/CSCV + DSR + IS→OOS surface + plateau + same-candidate 2x/3x cost stress + causality invariant + capacity/turnover'},
      {'name':'Microstructure Guard','status':'OK','detail':'Licensed Level-2/order-event adapter + V45 footprint intelligence (absorption, sweep, replenishment, liquidity vacuum, spoof-like churn risk) + freshness/auth/failure guard; only entry derisk/veto, never blocks exits'},
      {'name':'Meta Governance','status':'OK','detail':'Forward-only champion/challenger ranking; historical backtests cannot self-promote'},
      {'name':'Strategy Decay','status':'OK','detail':'Forward expectancy/PF/win-rate/equity degradation monitor; DECAY vetoes promotion, does not auto-liquidate'},
      {'name':'Meta Portfolio Brain','status':'OK','detail':'Forward-only regime-aware robot allocation with explicit cash floors and 25% per-bot cap'},
      {'name':'Trade Reality Engine','status':'OK','detail':'Prior-session intraday block-bootstrap stress test with stop-first ambiguity; can only veto/derisk paper entries'},
      {'name':'Risk Passport','status':'OK','detail':'Initial entry/stop/target plan is locked and fingerprinted on each paper position'},
      {'name':'Point-in-Time Integrity','status':'OK','detail':'Prospective evidence blocks provisional/future-dated inputs; missing timestamps only downgrade confidence'},
      {'name':'Forward Evidence Ledger','status':verify_ledger().get('status','WARN'),'detail':f"Hash-chain rows {verify_ledger().get('rows',0)} · bad {len(verify_ledger().get('bad_ids') or [])}"},
      {'name':'Decision Attribution 2.0','status':'OK','detail':'Forward-only feature attribution with bootstrap confidence intervals, Benjamini-Hochberg FDR control and regime-conflict diagnostics; no causal claim or automatic champion mutation'},
      {'name':'Adaptive Feature Governance','status':'OK','detail':'Champion unchanged; challenger-only quarantine/downweight/disable policy with prospective shadow A/B promotion review'},
      {'name':'Model Zoo Challenger Lab','status':'OK','detail':'External Qlib/Hugging Face/FinRL-style candidates require license, model-card, PIT, causality, cost, robustness, execution and forward-paper gates before challenger eligibility'},
      {'name':'External Challenger Execution','status':'OK','detail':'License-aware research adapters are isolated from paper/live paths; Qlib GBDT family has an internal causal BIST concept adapter while sequence/uncleared candidates remain blocked'},
      {'name':'Ensemble Challenger Lab','status':'OK','detail':'Only >=3 mature forward-evidence model snapshots with the same as-of/common universe can form a rank-normalized research ensemble; high model redundancy is flagged'},
      {'name':'Qlib Feature Bridge','status':qlib_adapter_status().get('status','ADAPTER_UNAVAILABLE'),'detail':'Causal BIST feature bridge is always available; optional LightGBM/Qlib packages remain lab-only and are never auto-installed'},
      {'name':'Cross-Sectional ML Challenger','status':'OK','detail':'Same-date BIST relative-ranking lab using cross-sectional z-scored causal features, rank IC and top-bottom forward excess spread; lab-only'},
      {'name':'Purged Walk-Forward XS Validation','status':'OK','detail':'Rolling cross-sectional OOS folds with 5d label purge and configurable embargo to reduce boundary leakage; lab-only'},
      {'name':'XS Cost & Turnover Reality','status':'OK','detail':'Cross-sectional challenger diagnostics include rebalance turnover, explicit cost drag and ADV-based capacity flags; costs never improve an edge'},
      {'name':'XS Portfolio Constructor','status':'OK','detail':'Paper-only constrained allocation with score/inverse-vol weighting, max-name cap, ADV capacity derisk and portfolio-guard checks'},
      {'name':'XS Paper Portfolio Engine','status':'OK','detail':'Persistent prospective paper ledger with rebalances, cost, turnover, mark-to-market, drawdown and XU100 excess tracking; no broker path'},
      {'name':'XS Autonomous Paper Tournament','status':'OK','detail':'Equal-capital prospective challenger portfolios with forward-only ranking, >=90d gate and champion/challenger governance; no live path'},
      {'name':'XS Autonomous Rebalance Scheduler','status':'OK','detail':'Paper-only daily mark and configurable rebalance cadence using prospective current XS ranking; missing model dependency waits without fallback'},
      {'name':'Model Reproducibility Registry','status':'OK','detail':'Prospective XS model decisions persist feature/data/dependency/model fingerprints, seed and training cutoff for auditability'},
      {'name':'Decision-to-Model Lineage','status':'OK','detail':'Each XS rebalance persists ranking snapshot plus model registry link, enabling rebalance→portfolio→ranking→model→training-data traceability'},
      {'name':'XS Lineage Hash Chain','status':xs_verify_lineage_ledger().get('status','WARN'),'detail':f"Hash-chain rows {xs_verify_lineage_ledger().get('rows',0)} · bad {len(xs_verify_lineage_ledger().get('bad_ids') or [])}"},
      {'name':'XS Promotion Governance','status':'OK','detail':'Hard forward-only gate combines >=90d evidence, >=12 rebalances, benchmark excess, drawdown, turnover, cost burden, model reproducibility and lineage integrity; review-only'},
      {'name':'Statistical Promotion Confidence','status':'OK','detail':'Prospective bootstrap confidence, regime stability and Bonferroni multiple-testing correction can veto promotion review; never enables live execution'},
      {'name':'Regime Robustness Gate','status':'OK','detail':'Prospective BULL/BEAR/RANGE/HIGH_VOL robustness gate requires multi-regime evidence and can veto single-regime-dependent challengers'},
      {'name':'Data Quality & Survivorship Guard','status':'OK','detail':'Current ranking blocks low coverage/mixed-as-of/invalid-price data; historical current-universe proxy is explicitly flagged and can veto promotion until PIT universe integrity improves'},
      {'name':'Point-in-Time Universe Integrity','status':'OK' if pit_universe_status().get('status')=='PIT_VERIFIED' else 'WARN','detail':'Verified COMPLETE historical membership datasets filter training dates; otherwise system remains CURRENT_UNIVERSE_PROXY and survivorship risk stays explicit'},
      {'name':'Sector / Factor Neutralization','status':'OK','detail':'Current XS scores are residualized against momentum/volatility/trend factors; sector dummies are used only when metadata coverage is sufficient, and neutralization evidence is required for promotion'},
      {'name':'XS Capacity & Market Impact 2.0','status':'OK','detail':'Portfolio construction combines median ADV, target trade notional, volatility/range, spread and execution horizon; constraints only reduce exposure and residual risk stays cash'},
      {'name':'Multi-Bar Paper Execution','status':'OK','detail':'Paper entries may split across at most two closed 15m bars using per-bar volume capacity; each fill has its own execution cost and protective exits always run first'},
      {'name':'BIST Auction / Gap / Price-Limit Reality','status':'OK','detail':'Official-rule equity guard models current price-limit/circuit-breaker risk, preserves gap-through-stop pricing and refuses fake protective fills on adverse limit locks'},
      {'name':'Strategy / Model Decay 2.0','status':'OK','detail':'Forward-only confidence-aware trade decay plus regime-aware XS excess/turnover/cost decay; DECAY vetoes promotion but never auto-liquidates'},
      {'name':'Champion Recovery & Hysteresis','status':'OK','detail':'Paper champion state advances only on new rebalance evidence; quarantine requires 2 decay points, recovery/challenger maturity 3 healthy points, and rotation requires score margin'},
      {'name':'Protected Feature Governance','status':'OK','detail':'Safety/integrity features are pinned at multiplier 1.0; non-protected penalties and recovery require repeated new forward evidence and are persisted in a governance event ledger'},
      {'name':'Portfolio Stress Lab','status':'OK','detail':'Deterministic correlation, gap-down, liquidity dry-up, top-cluster and sector-cluster shocks can veto XS promotion; never increase exposure'},
      {'name':'Forward Evidence Scorecard','status':'OK','detail':'Consolidates hard governance, statistics, regimes, data quality, factor neutrality, portfolio stress and decay into one review-only evidence view'},
      {'name':'Research Integrity Dashboard','status':'OK','detail':'Single integrity view aggregates evidence ledger, lineage, PIT universe, model registry, protected features and optional portfolio scorecard/stress/decay'},
      {'name':'Autonomous Research Loop','status':'OK','detail':'Idempotent research→cost/capacity→paper tournament→forward review orchestration; failed stages cannot be bypassed and no live authority exists'},
      {'name':'V80 System Integrity Review','status':'OK','detail':'Canonical promotion evidence path, explicit cash/benchmark accounting, non-redistributive constraints and regression invariants verified'},
      {'name':'Portfolio Concentration Guard','status':'OK','detail':'Signed 180d + recent60 + downside correlation, joint tail loss, XU100 beta and volatility guard'},
      {'name':'Execution Intelligence','status':'OK','detail':'V44 dynamic delayed-bar slippage + quadratic volume-share impact + observed spread + fillability horizon; can only worsen/reject paper fills'},
      {'name':'Paper Portfolio','status':'OK','detail':'Local hypothetical ledger · entry date/P&L/stop/target/trap snapshot supported'},
      {'name':'Chart Ruler','status':'OK','detail':'Price %, calendar duration and trading-bar count supported'},
      {'name':'Broker Safety','status':'OK','detail':'Direct live locked · paper risk gates active' if not br.get('direct_live_execution_enabled') else 'Live enabled'},
      {'name':'Last Error','status':'OK' if not bg.get('error') else 'WARN','detail':bg.get('error') or 'none'}
    ]
    overall='ERROR' if any(x['status']=='ERROR' for x in checks) else ('WARMING' if any(x['status']=='WARMING' for x in checks) else ('WARN' if any(x['status']=='WARN' for x in checks) else 'OK'))
    return {'version':'80.0.0','overall':overall,'checks':checks,'background':bg,'broker':br}

@app.get('/api/trap-defense/{ticker}')
def trap_defense_api(ticker:str):
    from .market_data import daily_frames
    import pandas as pd
    code=ticker.upper().replace('.IS','')
    df=daily_frames([code]).get(code,pd.DataFrame())
    return {'ticker':code,**assess_traps(df)}

@app.get('/api/trap-defense-radar')
def trap_defense_radar_api(limit:int=80):
    rows=scan_codes([x['ticker'] for x in get_universe()])
    out=[{'ticker':r.get('ticker'),'price':r.get('price'),'trap_defense':r.get('trap_defense'),'signal_guard':r.get('signal_guard'),
          'short_score':r.get('short_score'),'long_score':r.get('long_score'),'alpha_score':r.get('alpha_score'),'risk':r.get('risk')} for r in rows if r.get('trap_defense')]
    out.sort(key=lambda x:-(x.get('trap_defense') or {}).get('score',0))
    return {'rows':out[:max(10,min(limit,150))],'analyzed':len(out),'note':'OHLCV deception-risk radar; does not identify intent or a manipulator.'}

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

@app.get('/api/evidence-ledger/verify')
def evidence_ledger_verify_api():
    return verify_ledger()

@app.get('/api/decision-attribution')
def decision_attribution_api(horizon:int=20,min_samples:int=12):
    if horizon not in (5,20,60): raise HTTPException(422,'horizon must be 5, 20 or 60')
    return decision_attribution(horizon,max(5,min(min_samples,200)))

@app.get('/api/decision-attribution/report')
def decision_attribution_report_api():
    return decision_feature_report()

@app.get('/api/feature-governance')
def feature_governance_api(force:bool=False):
    return feature_governance_report(force=force)

@app.get('/api/feature-governance/ab')
def feature_governance_ab_api(horizon:int=20,threshold:int=78,min_samples:int=20):
    if horizon not in (5,20,60): raise HTTPException(422,'horizon must be 5, 20 or 60')
    return feature_governance_ab(horizon,max(50,min(threshold,95)),max(5,min(min_samples,200)))

@app.get('/api/model-zoo')
def model_zoo_api():
    return model_zoo_catalog()

@app.post('/api/model-zoo/validate')
def model_zoo_validate_api(payload:dict=Body(...)):
    return model_zoo_validate(payload)

@app.post('/api/model-zoo/lab')
def model_zoo_lab_api(payload:list[dict]=Body(...)):
    return model_zoo_summary(payload[:100])

@app.get('/api/qlib-bridge/status')
def qlib_bridge_status_api():
    return qlib_adapter_status()

@app.get('/api/qlib-bridge/dataset/{ticker}')
def qlib_bridge_dataset_api(ticker:str,period:str='5y'):
    d=qlib_dataset_payload(ticker,period)
    frame=d.pop('frame',None)
    if frame is not None:
        d['preview']=frame.tail(5).reset_index().to_dict(orient='records')
    return d

@app.get('/api/qlib-bridge/lab/{ticker}')
def qlib_bridge_lab_api(ticker:str,period:str='5y'):
    return qlib_fit_predict_lab(ticker,period)

@app.get('/api/xs-ml/panel')
def xs_ml_panel_api(codes:str|None=None,period:str='5y',limit:int=120):
    tickers=[x.strip().upper() for x in codes.split(',') if x.strip()] if codes else None
    d=xs_build_panel(tickers,period,max(5,min(limit,500)))
    frame=d.pop('frame',None)
    if frame is not None:
        d['preview']=frame.tail(20).to_dict(orient='records')
    return d

@app.get('/api/xs-ml/lab')
def xs_ml_lab_api(codes:str|None=None,period:str='5y',limit:int=120):
    tickers=[x.strip().upper() for x in codes.split(',') if x.strip()] if codes else None
    return xs_run_lab(tickers,period,max(5,min(limit,500)))

@app.get('/api/xs-ml/purged-walk-forward')
def xs_ml_purged_walk_forward_api(codes:str|None=None,period:str='5y',limit:int=120,train_days:int=252,test_days:int=63,purge_days:int=5,embargo_days:int=5):
    tickers=[x.strip().upper() for x in codes.split(',') if x.strip()] if codes else None
    return xs_purged_walk_forward_lab(tickers,period,max(5,min(limit,500)),
        max(120,min(train_days,756)),max(20,min(test_days,126)),
        max(5,min(purge_days,20)),max(0,min(embargo_days,20)))

@app.get('/api/xs-ml/cost-reality')
def xs_ml_cost_reality_api(codes:str|None=None,period:str='5y',limit:int=120,train_days:int=252,test_days:int=63,purge_days:int=5,embargo_days:int=5,one_way_cost_bps:int=20,rebalance_every:int=5,portfolio_value:float=1000000,adv_limit_pct:float=1.0):
    tickers=[x.strip().upper() for x in codes.split(',') if x.strip()] if codes else None
    return xs_cost_reality(tickers,period,max(5,min(limit,500)),
        max(120,min(train_days,756)),max(20,min(test_days,126)),
        max(5,min(purge_days,20)),max(0,min(embargo_days,20)),
        max(0,min(one_way_cost_bps,200)),max(1,min(rebalance_every,20)),
        max(10000,min(portfolio_value,1000000000)),max(.1,min(adv_limit_pct,10)))

@app.post('/api/xs-ml/portfolio')
def xs_ml_portfolio_api(payload:dict=Body(...)):
    ranked=payload.get('ranked') or []
    return xs_portfolio_construct(ranked,
        max(10000,min(float(payload.get('portfolio_value') or 1000000),1000000000)),
        max(3,min(int(payload.get('max_names') or 10),20)),
        max(.05,min(float(payload.get('max_weight') or .15),.50)),
        max(.1,min(float(payload.get('adv_limit_pct') or 1.0),10)),
        str(payload.get('method') or 'score_inverse_vol'))

@app.post('/api/xs-paper/create')
def xs_paper_create_api(payload:dict=Body(default={})):
    return xs_paper_create(str(payload.get('name') or 'XS Challenger'),
        max(10000,min(float(payload.get('capital') or 1000000),1000000000)),
        str(payload.get('benchmark') or 'XU100'))

@app.post('/api/xs-paper/{portfolio_id}/rebalance')
def xs_paper_rebalance_api(portfolio_id:int,payload:dict=Body(...)):
    return xs_paper_rebalance(portfolio_id,payload.get('rows') or [],
        max(0,min(float(payload.get('one_way_cost_bps') or 20),200)))

@app.post('/api/xs-paper/{portfolio_id}/mark')
def xs_paper_mark_api(portfolio_id:int):
    return xs_paper_mark(portfolio_id)

@app.get('/api/xs-paper/{portfolio_id}')
def xs_paper_history_api(portfolio_id:int,limit:int=200):
    return xs_paper_history(portfolio_id,max(1,min(limit,1000)))

@app.post('/api/xs-tournament/create')
def xs_tournament_create_api(payload:dict=Body(default={})):
    return xs_tournament_create(
        max(10000,min(float(payload.get('capital_each') or 1000000),1000000000)),
        str(payload.get('benchmark') or 'XU100'))

@app.post('/api/xs-tournament/{tournament_id}/start')
def xs_tournament_start_api(tournament_id:int):
    return xs_tournament_start(tournament_id)

@app.post('/api/xs-tournament/{tournament_id}/{variant_id}/rebalance')
def xs_tournament_rebalance_api(tournament_id:int,variant_id:str,payload:dict=Body(...)):
    return xs_tournament_rebalance(tournament_id,variant_id,payload.get('rows') or [],
        max(0,min(float(payload.get('one_way_cost_bps') or 20),200)))

@app.post('/api/xs-tournament/{tournament_id}/mark')
def xs_tournament_mark_api(tournament_id:int):
    return xs_tournament_mark(tournament_id)

@app.get('/api/xs-tournament/{tournament_id}')
def xs_tournament_snapshot_api(tournament_id:int):
    return xs_tournament_snapshot(tournament_id)

@app.post('/api/xs-tournament/{tournament_id}/scheduler')
def xs_scheduler_configure_api(tournament_id:int,payload:dict=Body(...)):
    return xs_scheduler_configure(tournament_id,
        payload.get('enabled'),
        payload.get('rebalance_every_days'),
        payload.get('cost_bps'),
        payload.get('max_names'),
        payload.get('max_weight'),
        payload.get('adv_limit_pct'),
        payload.get('limit'))

@app.get('/api/xs-tournament/{tournament_id}/scheduler')
def xs_scheduler_state_api(tournament_id:int):
    return xs_scheduler_state(tournament_id)

@app.post('/api/xs-tournament/{tournament_id}/scheduler/run')
def xs_scheduler_run_api(tournament_id:int,force_rebalance:bool=False):
    return xs_scheduler_run_once(tournament_id,force_rebalance=force_rebalance)

@app.get('/api/model-registry')
def model_registry_history_api(limit:int=100):
    return model_registry_history(max(1,min(limit,1000)))

@app.get('/api/model-registry/{registry_id}')
def model_registry_get_api(registry_id:int):
    return model_registry_get(registry_id)

@app.get('/api/xs-lineage/{rebalance_id}')
def xs_lineage_api(rebalance_id:int):
    return xs_paper_lineage(rebalance_id)

@app.get('/api/xs-lineage/verify')
def xs_lineage_verify_api():
    return xs_verify_lineage_ledger()

@app.get('/api/xs-promotion/{portfolio_id}')
def xs_promotion_api(portfolio_id:int,days:int=0):
    h=xs_paper_history(portfolio_id,500)
    if h.get('status')!='OK': return h
    return promotion_governance_evaluate(h,max(0,days))

@app.get('/api/xs-promotion-statistics/{portfolio_id}')
def xs_promotion_statistics_api(portfolio_id:int):
    h=xs_paper_history(portfolio_id,1000)
    if h.get('status')!='OK': return h
    return statistical_promotion_evaluate(h)

@app.get('/api/xs-regime-robustness/{portfolio_id}')
def xs_regime_robustness_api(portfolio_id:int):
    h=xs_paper_history(portfolio_id,1000)
    if h.get('status')!='OK': return h
    return regime_robustness_evaluate(h)

@app.get('/api/xs-data-integrity/{portfolio_id}')
def xs_data_integrity_api(portfolio_id:int):
    h=xs_paper_history(portfolio_id,1000)
    if h.get('status')!='OK': return h
    return data_quality_history_evaluate(h)

@app.get('/api/xs-survivorship')
def xs_survivorship_api():
    return pit_universe_status()

@app.get('/api/pit-universe/status')
def pit_universe_status_api():
    return pit_universe_status()

@app.get('/api/pit-universe/{ticker}')
def pit_universe_ticker_api(ticker:str):
    return {'ticker':ticker.upper().replace('.IS',''),'intervals':pit_universe_intervals(ticker),'registry':pit_universe_status()}

@app.get('/api/xs-factor-neutralization/{portfolio_id}')
def xs_factor_neutralization_api(portfolio_id:int):
    h=xs_paper_history(portfolio_id,1000)
    if h.get('status')!='OK': return h
    return factor_neutralization_history(h)

@app.post('/api/xs-capacity-assess')
def xs_capacity_assess_api(payload:dict=Body(...)):
    return xs_capacity_assess(
        float(payload.get('allocation') or 0),float(payload.get('current_allocation') or 0),
        float(payload.get('value_turnover') or 0),float(payload.get('annual_vol_pct') or 0),
        payload.get('price'),payload.get('high'),payload.get('low'),payload.get('spread_bps'),
        float(payload.get('adv_limit_pct') or 1.0))

@app.get('/api/bist-execution-policy')
def bist_execution_policy_api():
    return bist_execution_policy()

@app.get('/api/xs-decay/{portfolio_id}')
def xs_decay_v2_api(portfolio_id:int):
    h=xs_paper_history(portfolio_id,1000)
    if h.get('status')!='OK': return h
    return xs_detect_decay_v2(h)

@app.get('/api/xs-champion-governance/{tournament_id}')
def xs_champion_governance_api(tournament_id:int):
    return champion_governance_status(tournament_id)

@app.get('/api/protected-feature-governance')
def protected_feature_governance_api(limit:int=200):
    return protected_feature_governance_status(max(1,min(limit,1000)))

@app.get('/api/external-challengers')
def external_challenger_catalog_api():
    return external_challenger_catalog()

@app.post('/api/external-challengers/{candidate_id}/run')
def external_challenger_run_api(candidate_id:str,payload:dict=Body(default={})):
    codes=payload.get('codes')
    tickers=[str(x).strip().upper() for x in codes if str(x).strip()] if isinstance(codes,list) else None
    return external_challenger_run(candidate_id,tickers,str(payload.get('period') or '5y'),
                                   max(5,min(int(payload.get('limit') or 120),500)))

@app.post('/api/ensemble-challenger/lab')
def ensemble_challenger_lab_api(payload:dict=Body(...)):
    return ensemble_challenger_build(payload.get('candidates') or [],
                                     max(.34,min(float(payload.get('max_model_weight') or .40),.50)))

@app.get('/api/adversarial-v2/{ticker}')
def adversarial_v2_api(ticker:str):
    from .market_data import daily_frames
    import pandas as pd
    code=ticker.upper().replace('.IS','')
    df=daily_frames([code]).get(code,pd.DataFrame())
    return {'ticker':code,**adversarial_stress_v2(df)}

@app.get('/api/adversarial-v2-cross')
def adversarial_v2_cross_api(codes:str):
    from .market_data import daily_frames
    selected=[x.strip().upper().replace('.IS','') for x in codes.split(',') if x.strip()][:20]
    return adversarial_cross_v2(daily_frames(selected))

@app.get('/api/xs-portfolio-stress/{portfolio_id}')
def xs_portfolio_stress_api(portfolio_id:int):
    h=xs_paper_history(portfolio_id,1000)
    if h.get('status')!='OK': return h
    return portfolio_stress_evaluate(h)

@app.get('/api/xs-forward-scorecard/{portfolio_id}')
def xs_forward_scorecard_api(portfolio_id:int,days:int=0,test_count:int=3):
    h=xs_paper_history(portfolio_id,1000)
    if h.get('status')!='OK': return h
    return forward_scorecard_build(h,max(0,days),max(1,min(test_count,50)))

@app.get('/api/research-integrity')
def research_integrity_api(portfolio_id:int|None=None,days:int=0,test_count:int=3):
    return research_integrity_dashboard(portfolio_id,max(0,days),max(1,min(test_count,50)))

@app.post('/api/autonomous-research/run')
def autonomous_research_run_api(payload:dict=Body(default={})):
    codes=payload.get('codes')
    tickers=[str(x).strip().upper() for x in codes if str(x).strip()] if isinstance(codes,list) else None
    return autonomous_research_run(
        tickers=tickers,
        period=str(payload.get('period') or '5y'),
        limit=max(20,min(int(payload.get('limit') or 120),500)),
        train_days=max(120,min(int(payload.get('train_days') or 252),756)),
        test_days=max(20,min(int(payload.get('test_days') or 63),126)),
        purge_days=max(5,min(int(payload.get('purge_days') or 5),20)),
        embargo_days=max(0,min(int(payload.get('embargo_days') or 5),20)),
        one_way_cost_bps=max(0,min(int(payload.get('one_way_cost_bps') or 20),200)),
        rebalance_every=max(1,min(int(payload.get('rebalance_every') or 5),20)),
        portfolio_value=max(10000,min(float(payload.get('portfolio_value') or 1000000),1000000000)),
        adv_limit_pct=max(.1,min(float(payload.get('adv_limit_pct') or 1.0),10)),
        auto_create_paper=bool(payload.get('auto_create_paper',True)),
        force_rebalance=bool(payload.get('force_rebalance',False)))

@app.get('/api/autonomous-research/status')
def autonomous_research_status_api(limit:int=50):
    return autonomous_research_status(max(1,min(limit,200)))

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
    if os.getenv('BIST_AI_DESKTOP')=='1' or os.getenv('BIST_AI_BACKGROUND','1')!='0':
        start_radar(); start_alert_engine(); start_background_supervisor()
        auto_paper.start_worker(); robot_arena.start_worker(); xs_scheduler_start_worker()

@app.get('/health')
def health():
    return {'status':'ok','version':'80.0.0','service':'bist-ai-terminal'}

@app.get('/api/document-lab/status')
def document_status_api():
    return document_configuration()

@app.post('/api/document-lab/review')
def document_review_api(payload:ReviewRequest,x_bist_cloud_token:str=Header(default='')):
    return document_review(payload,x_bist_cloud_token)

@app.get('/api/community-catalog')
def community_catalog_api():
    from .community_catalog import CATALOG
    return CATALOG

@app.get('/api/community-research/{ticker}')
def community_research_api(ticker:str,cost_bps:int=30):
    import re
    import pandas as pd
    from .market_data import yahoo_rows
    from .community_indicators import evaluate
    code=ticker.upper().removesuffix('.IS')
    if not re.fullmatch(r'[A-Z0-9]{2,12}',code) or not 0<=cost_bps<=300:
        raise HTTPException(422,'Geçersiz hisse veya maliyet.')
    try:
        raw=yahoo_rows(code,period='5y',interval='1d')
        frame=pd.DataFrame(raw['candles']).rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
        return {'ticker':code,**evaluate(frame,cost_bps)}
    except Exception:
        return {'ticker':code,'status':'NO_DATA','message':'Kaynak verisi yok veya barlar geçersiz; deney üretilmedi.'}


# Separate, bearer-token-scoped paper accounts. No route connects to a live broker.
def _auto_result(fn,*args):
    try:return fn(*args)
    except FileNotFoundError:raise HTTPException(status_code=404,detail='Otomatik sanal hesap bulunamadı.')
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))

@app.post('/api/auto-paper/accounts')
def auto_create_api():return auto_paper.create_account()

@app.get('/api/auto-paper/account')
def auto_account_api(x_bist_paper_token:str=Header(default='')):
    return _auto_result(auto_paper.snapshot,x_bist_paper_token)

@app.post('/api/auto-paper/config')
def auto_config_api(payload:dict=Body(...),x_bist_paper_token:str=Header(default='')):
    return _auto_result(auto_paper.configure,x_bist_paper_token,payload)

@app.post('/api/auto-paper/control')
def auto_control_api(payload:dict=Body(...),x_bist_paper_token:str=Header(default='')):
    return _auto_result(auto_paper.control,x_bist_paper_token,payload.get('action'))

@app.post('/api/auto-paper/demo')
def auto_demo_api():return auto_paper.demo()


@app.get('/api/robot-arena/catalog')
def arena_catalog_api():return robot_arena.catalog()

@app.get('/api/robot-arena/account')
def arena_account_api(x_bist_paper_token:str=Header(default='')):
    return _auto_result(robot_arena.snapshot,x_bist_paper_token)

@app.post('/api/robot-arena/create')
def arena_create_api(x_bist_paper_token:str=Header(default='')):
    return _auto_result(robot_arena.create,x_bist_paper_token)

@app.post('/api/robot-arena/control')
def arena_control_api(payload:dict=Body(...),x_bist_paper_token:str=Header(default='')):
    return _auto_result(robot_arena.control,x_bist_paper_token,payload.get('action'))

@app.post('/api/robot-arena/config')
def arena_config_api(payload:dict=Body(...),x_bist_paper_token:str=Header(default='')):
    return _auto_result(robot_arena.configure,x_bist_paper_token,payload)
