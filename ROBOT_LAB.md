# Robot Laboratuvarı — V28.0

Six prospective, separate paper accounts: existing Closed Daily Trend, independently implemented AlphaTrend, OTT, TOTT, transparent Relative Momentum, and original Codex Regime & Confirmation. This is an experiment, not a validated profitable robot. No real orders or vendor account credentials are used. Existing autonomous/manual portfolios are not migrated or reset.

## Common experiment policy

Each account starts paused with 1,000,000 TRY. One start action timestamps all six; one shared scan uses the KAP universe and closed daily OHLCV. Coverage must reach 80% of the full universe before any new entry. All entries require >=200 daily bars, CLEAR data guard, >=10m TRY average turnover, finite ATR, and risk <80. A signal date cannot trigger a second entry in the same bot, even after a rejection or exit. Candidates are deterministically ranked, with no named ticker bonus.

All bots use the same sizing/execution: max six positions, max 10% per position and 60% gross, 0.5% planned stop risk, 2% daily loss halt and 10% drawdown halt. Stop distance is max(2 ATR, 2% of fill reference); target 2R. A gap may exceed planned stop loss. Commission defaults to 10bps per side and slippage 10bps per side. At most 1% of observed 15-minute volume per simulated entry. Shorting is off by default; optional simulated shorts reserve 100% cash collateral and charge 15% annual hypothetical borrow. Momentum and Codex remain long-only. Short availability, eligibility and corporate action accounting are not verified.

Only commission, slippage and simulated-short permission may change, and only before the first start. No reset or per-bot pause endpoint exists. Pause cancels entries and retains protective checks; close-all queues exits for subsequent valid quotes. Data retrieval cannot override a pause issued while a request is in flight. All ledger mutations re-read the latest disk state under a lock.

A decision is recorded after scan data retrieval. Fills use only a complete 15-minute bar starting after the decision. Existing stop/target checks precede pending orders; if both levels occur in a bar, stop is assumed first. Delayed prices, not actual fills. Independent scan/risk workers; common quote union is downloaded once for all bots. Scan reuses the shared OHLCV cache, immediately advances batches, and waits 10 minutes after a complete sweep. Risk checks target 30 seconds, subject to provider latency. Worker threads run while the server/application is running.

## Independent strategy versions

Community formulas are independently implemented from published mathematical descriptions, not copied vendor code, not official integrations, and not verified bar-for-bar Pine ports. No third-party profit claims seed this experiment. ATR initialization, moving-average implementation, provider/session differences can change signals. All rules are fixed version 1 and have not been optimized against a selected historical winner.

* AlphaTrend: MFI14, SMA14 true range ×1 trailing rail, compare rail with lag2. Bull state enters long; bear state exits or, if common short setting permits, enters short. Plateau holds. Rank by liquid turnover.
* OTT: VIDYA length2, absolute CMO9 adaptive coefficient, percent1.4 trailing rail/adjustment, lag2 line. Compare current support average with lag2 OTT. Equal means no signal. Rank by liquid turnover.
* TOTT: same independent OTT construction with VIDYA40, percent1, lag2 and ±0.6% dead band. Above upper band enters; below lower band exits. Inside band holds. Rank by liquid turnover.
* Momentum: long only, price above EMA50, relative strength20 and60 positive, ADX>=20, RSI45–70. Rank by RS20+0.5RS60, exit below EMA50.
* Codex Regime & Confirmation: long only; XU100 above EMA50 and EMA50 rising over five bars, same benchmark bar date; >=80% feature coverage and >=55% of valid universe above EMA50; RS20/60 positive; ADX>=22, RSI45–68; volume>=1.2× prior20 average; close above previous20 highs; close in upper35% of daily range, upper wick<=25%; opening gap<=1.5 ATR14 Wilder, extension above EMA20 between0 and2 ATR. Exit below EMA20 or broken benchmark regime; missing benchmark alone does not force an exit. Rank by RS20+0.5RS60. These filters attempt to reject weak breakouts, they do not identify intent or guarantee protection from manipulation. It is a deterministic algorithm authored for this app, not a trained AI model.

## Results and references

Net return includes marked open P/L, entry/exit fees and borrow costs. Costs and closed-trade totals persist independently of retained display logs (up to2,000 stored orders, last200 exposed per bot). Maximum drawdown persists from observed ledger valuations, not every tick/intrabar excursion. Unavailable/stale held quotes are flagged; their most recent price remains the valuation reference. Curves retain the latest2,000 samples (500 exposed); no annualized return or Sharpe is manufactured from short samples. Profit factor stays unavailable when no losing close exists. Zero trades means no evidence, not success. Never automatically declares a validated winner.

XU100 benchmark anchors on the first fresh, complete 15-minute bar starting after experiment start. It is a costless price-index reference, not an executable instrument, excludes dividends and cash interest, and is timestamped. A second reference is 60% index +40% zero-interest cash. No retroactive pre-start benchmark return. Paused experiments continue benchmark/risk observations; index last-quote time remains visible on unavailable data.

Comparison is forward paper only. Historical return, point-in-time fundamentals, survivorship-clean backtest, risk-free-adjusted Sharpe and independent live account verification are not supplied in this version. No claim of best BIST performance. Candidate filters mean realized exposures differ even though policy/capital are common.

## External products, not connected

QNB Akıllı Robo, Roboritma, YatırımUzmanı, Matriks/iDeal, Finemar, Parada Pusula, Holly, Tickeron, Danelfin and FinRL are research references in a clearly separate list. Closed formulas/API entitlements are unavailable; none is secretly recreated under a vendor name. No copied vendor strategy or unauthorized integration is represented as installed. Published performance figures never enter the leaderboard.

Sources:
- AlphaTrend: https://www.tradingview.com/script/3wdQu7P3-AlphaTrend-Strategy/ (Kıvanç Özbilgiç)
- OTT: https://www.tradingview.com/script/HPbRZvsV/ (Anıl Özekşi / Kıvanç Özbilgiç)
- TOTT: https://www.tradingview.com/script/eENf7NpJ/ (Anıl Özekşi / Kıvanç Özbilgiç)

## Storage/API

`BIST_ROBOT_ARENA_DIR` overrides the default app-data `robot-arena` directory. Bearer token remains in the existing origin-scoped paper token store and travels in `X-Bist-Paper-Token`, never a query URL. Files keyed by SHA256 token, atomic replace, mode0600; separate from existing auto-paper files. Missing account creates nothing automatically; explicit Create is idempotent, preserves an existing experiment, and never resets a ledger. Ephemeral server redeploys can lose files; the UI states this plainly. Persistent desktop app-data is preferred for long forward tests.

GET `/api/robot-arena/catalog`, authenticated GET `/account`, POST `/create`, POST `/config`, POST `/control`. No live mode or reset endpoint. Notification IDs include bot IDs; fills, risk halts and fresh large position moves go to the existing notification panel while the laboratory is open.
