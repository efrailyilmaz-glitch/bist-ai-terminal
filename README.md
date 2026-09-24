# BIST AI Terminal V3

Premium quantitative research terminal for Borsa Istanbul.

## V3 features

- Dynamic BIST company universe from KAP (no hard-coded 28-stock list)
- Progressive whole-universe scanner
- Short-horizon score: momentum, volume, breakout, RSI, MA20/50
- Long-horizon score: MA50/200, 3–6 month momentum, volatility filter
- Composite alpha, risk, smart-money proxy and anomaly scores
- TradingView Lightweight Charts candlesticks, volume and MA20/50/200
- 1M / 3M / 6M / 1Y / 2Y / 5Y ranges and intraday/daily/weekly intervals
- Global regime inputs: BIST 100, S&P 500, Nasdaq, DXY, US10Y, USD/TRY, EUR/TRY, gold and oil
- Historical MA20/50 backtest with return, benchmark, alpha, Sharpe, drawdown and trade count
- Model portfolio research basket
- KAP universe integration and honest data-source/status labels
- CI validation + Render auto deploy

## Data policy

LIVE, PARTIAL, CACHE and unavailable states must be shown honestly. The application does not fabricate Level-2 order book, custody/takas, fund-flow or real-time KAP REST data. Those layers require an appropriate licensed/official provider.

## Local run

```bash
pip install -r requirements.txt
bash run.sh
```

Open http://localhost:8000

Health endpoint: `/health`

## Deployment

Render configuration is in `render.yaml`. The service is configured for deploy-on-commit from the linked branch.
