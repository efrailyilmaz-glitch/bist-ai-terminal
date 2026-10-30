# Robot Laboratuvarı — V34.0

V34 is a prospective paper-trading research laboratory. It does not authorize live trading, claim guaranteed profitability, or copy proprietary vendor code. The objective is robustness: reject fragile strategies before they can influence capital.

## Architecture

Signal Engines → Regime Router → Trap Defense → Robustness Gate → Adaptive Risk → Paper Execution → Forward Champion/Challenger Governance.

The catalog includes baseline trend logic plus independent implementations/adaptations of AlphaTrend, OTT, TOTT, relative/time-series momentum, Donchian breakout, regime-filtered mean reversion, low-volatility breakout, defensive momentum, Codex strategies, QQE+SSL+WAE fusion, KAMA efficiency regime and the Regime Meta Router. Community formulas are implemented from public mathematical descriptions only; no closed Pine/vendor source is copied.

## Common policy

Each bot starts with 1,000,000 TRY in an isolated paper account. Common defaults: max six positions, 10% max position, 60% gross exposure, 0.5% planned stop risk, 2% daily loss halt, 10% drawdown halt, 10 bps commission and 10 bps slippage per side. Entries require closed bars, sufficient history, liquidity, CLEAR signal/trap guards and deterministic ranking.

Adaptive risk can only reduce exposure. Breadth deterioration, higher security risk, benchmark weakness and volatility expansion lower the position/risk multiplier; the multiplier never exceeds 1.0. No leverage boost is created by a strong signal.

## Robustness gate

Historical research is deliberately treated as suspect until it survives:

- PBO/CSCV candidate-family overfitting diagnostic.
- Deflated Sharpe Ratio adjustment for multiple testing and non-normal returns.
- Walk-forward IS→OOS parameter-surface correlation.
- Parameter-plateau width check; a single sharp optimum is considered fragile.
- 2x and 3x transaction-cost stress.
- Synthetic adversarial scenarios: fake breakout, gap trap, stop sweep, volume climax and pump-fade.

Passing the robustness gate only makes a strategy eligible for locked prospective paper testing. It never authorizes live execution.

## Forward champion/challenger governance

Historical backtests cannot promote themselves. Forward bots are ranked with small-sample shrinkage and drawdown/cost penalties. Challenger eligibility requires at least 90 calendar days, 30 closed trades, profit factor >=1.2, max drawdown <=8% and benchmark excess return. A challenger must beat the incumbent by a material score margin before nomination, reducing strategy churn. Nomination remains a paper-governance event only.

## Microstructure guard

V34 includes an adapter-neutral microstructure guard for licensed/authorized market-depth and order-event data. It can evaluate spread, multi-level book imbalance, signed order-flow pressure and cancellation asymmetry.

Missing microstructure data returns UNKNOWN and cannot create bullish evidence. BAD/CAUTION states can reduce risk or veto entries. GOOD status cannot increase leverage or bypass higher-level risk gates.

This distinction matters because OHLCV cannot prove spoofing or manipulative intent. True short-horizon order-flow analysis requires authorized Level-2/order-event information.

## Execution realism

Paper fills use complete delayed 15-minute bars beginning after the recorded decision. Existing protective exits are evaluated before new pending fills. A same-bar trailing stop cannot look ahead. Gap risk can exceed planned stop loss. Liquidity sizing is capped against observed volume. Costs and hypothetical short borrow are tracked.

The experiment remains provider-dependent. Survivorship-clean point-in-time universes, corporate-action-perfect histories, exact real broker fills and full exchange microstructure history require licensed data sources.

## Interpretation

Zero trades is no evidence. A high historical Sharpe is no proof. A single winning parameter is a warning, not a trophy. The preferred strategy is the one that remains useful across regimes, costs, adversarial tests and prospective observations with controlled drawdown.

There is intentionally no “validated forever” state. A champion remains subject to regime change, data-quality halts and challenger review.
