# BIST AI Quant Research Terminal V5

Borsa İstanbul için tüm-evren teknik tarama, temel faktör analizi, KAP/haber araştırması, strateji doğrulama ve portföy risk yönetimini bir araya getiren research terminal.

## V5 modülleri

### Universe & Data
- Dinamik KAP BIST şirket evreni
- Yahoo Finance BIST fiyat serileri ve dayanıklı chunked scanner
- LIVE / PARTIAL / N/A durum etiketleri
- Data Health ve provider registry
- Lisanslı market/KAP/news/broker provider ENV readiness

### Technical & Structure
- RSI, Stochastic RSI, MACD, ADX/+DI/-DI
- Bollinger, ATR, MFI, OBV
- EMA20/50/200 ve XU100 relative strength
- Supertrend, Ichimoku
- bullish/bearish RSI ve MACD divergence
- Golden/Death Cross
- Bollinger squeeze
- otomatik pivot-cluster destek/direnç
- 15dk / 1sa / 4sa / günlük / haftalık MTF consensus
- 52 haftalık konum ve ortalama işlem değeri

### Whole-Market Research
- Kısa Vade Alpha Radar
- Uzun Vade Alpha Radar
- Setup Radar
- Anomaly Radar
- Market Internals: advance breadth, EMA participation, 52H participation, trend breadth
- Signal Inbox
- Premium Screener presets
- short/long/risk/ADX/relative-strength/likidite filtreleri
- Tüm BIST görünümü varsayılan olarak tam evreni korur

### Fundamental & Factor Engine
- Value / Quality / Growth / Balance / Shareholder Return
- sektör-duyarlı skor: finansal şirketler ayrı model
- F/K, PD/DD, FD/FAVÖK, F/S, FCF Yield
- ROE/ROA/marjlar
- gelir/kâr büyümesi
- borç, likidite ve net borç
- TTM gelir/net kâr/FCF/OCF
- FCF ve işletme nakit dönüşümü
- temettü ve payout
- veri coverage/confidence
- Factor Lab ve yüklenen örneklem içinde sektör faktör özeti
- analist hedefi yalnız referans; research score'a dahil değildir

### KAP / News / Catalysts
- KAP şirket profili
- sektör/pazar/endeks ve rapor takvimi
- KAP olay taxonomy: iş ilişkisi, yatırım, shareholder return, sermaye aksiyonu, ortak işlemleri, hukuki/operasyonel/finansman riskleri
- materiality ve sentiment ayrı
- Google News RSS headline sentiment
- Catalyst Calendar: Watchlist veya top-alpha hisseler
- lisanslı real-time KAP varmış gibi sahte feed yok

### V5 Research Engine
- Teknik + Fundamental + KAP + News + Macro
- ayrı kısa ve uzun research score
- confidence / coverage
- strengths & red flags
- risk/anomaly penalty
- Research Journal ile tarayıcıda model snapshot ve tez takibi

### TradingView-style Chart
- Candlestick + volume
- EMA20/50/200
- Bollinger
- Supertrend
- Ichimoku
- otomatik S/R
- RSI/Stoch pane
- MACD pane
- indicator toggle

### Strategy Lab
- EMA trend
- momentum
- breakout
- RSI mean reversion
- Supertrend
- komisyon + slippage
- CAGR, Sharpe, Sortino, Calmar
- max drawdown, profit factor, exposure
- günlük VaR95/CVaR95
- buy-and-hold benchmark
- çoklu strateji karşılaştırma
- walk-forward / out-of-sample optimizasyon
- block-bootstrap Monte Carlo P10/median/P90 dağılımı

### Portfolio Risk Lab
- equal weight
- inverse volatility
- minimum variance
- approximate risk parity
- allocation method comparison
- korelasyon matrisi
- XU100 beta
- volatility, VaR, CVaR
- drawdown
- risk contribution
- stress test
- block-bootstrap portfolio Monte Carlo
- diversification score

### Productivity
- Watchlist (browser-local)
- Research Journal (browser-local)
- CSV export
- Signal Inbox
- Catalyst Calendar
- Data Health / Model Governance
- GitHub CI + Render deploy-on-commit

## Model Governance / Known limitations
- Current company universe can create survivorship bias for historical universe-level analysis.
- Yahoo is a third-party/delayed source; missing or revised values are possible.
- Financial-statement comparability varies by sector and reporting regime.
- Turkish inflation accounting (TMS/TAS 29) can materially affect historical ratio comparability.
- Headline sentiment scores titles, not full article bodies.
- KAP public-page parsing is not licensed real-time KAP REST distribution.
- Smart-money/anomaly are price-volume proxies; not takas, custody, Level-2 or proof of manipulation.
- Monte Carlo is a historical return-distribution stress tool, not a future price forecast.
- Live broker execution stays disabled until an official documented provider is configured.

## Local

```bash
pip install -r requirements.txt
bash run.sh
```

Health: `/health`  
Data health: `/api/data-health`  
Model card: `/api/model-card`

## Deployment
`render.yaml` is configured for commit-based deployment from the linked main branch.

## Disclaimer
Research/model outputs are not guarantees and are not personalized investment advice.
