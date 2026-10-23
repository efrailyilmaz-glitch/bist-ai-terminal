# Automatic paper trading — V27.1

This engine only writes simulated account records. It imports no broker submission API and exposes no live execution mode. The manual chart paper account is separate.

## Use

Open **Otomatik Sanal İşlem**. A private simulated account starts with TL 1,000,000. Review settings, then select **Otomatik işlemi başlat**. **Yeni girişleri durdur** cancels pending entries while protective exits continue. **Tümünü kapat ve durdur** queues exits; it waits for a subsequent valid price and does not fabricate a fill. The engine runs while the Python server/application process is running. Desktop files persist under the existing application data directory. Browser access uses a device-stored random bearer token in a header; URLs and snapshots do not expose it.

## Fixed strategy

- At least 200 closed daily bars; no open daily bar in either features or benchmark.
- Long: short score >=75, long score >=68, positive MACD histogram, bullish Supertrend, ADX >=22, RSI 45–72.
- Short: short score <=30, long score <=40, negative MACD histogram, bearish Supertrend, ADX >=25, RSI 28–55.
- Both: CLEAR guard, risk <80, average daily turnover >=TL 10m, valid ATR.
- Only a complete KAP universe scan with at least 80% same-date available data can queue entries by default. A fallback 15-stock list cannot trade. Ties use risk then ticker for deterministic display; no ticker has a special preference.
- Default 6 positions, 10% equity per symbol, 60% gross exposure, planned stop risk 0.5% equity. Size also respects cash, 1% of the fill bar volume and estimated round-trip costs.
- Stop distance is max(2 ATR, 2% price); target is 2 times that distance. Trend reversal can queue an exit even if universe coverage is insufficient for new entries. Symbol/date dedup prevents churning into the same daily signal.

## Forward fill model

Yahoo delayed 15-minute bars are used. The bar must be complete, have positive volume and valid OHLC, be from the current Istanbul weekday, and have ended within 45 minutes. Its start must be at or after the decision record time. Retrieval completion, not request start, timestamps a decision. Fill is its close plus adverse configured slippage. A decision expires after 48 hours without a suitable fill. There is no same-bar entry/stop look-ahead.

Existing stop/target orders use subsequent OHLC. When both are touched, stop wins. A stop gap uses the worse opening price; slippage/fees are additional. Targets use the target without optimistic opening-price improvement. Duplicate/out-of-order bars cannot fill twice. Large price scale jumps are held for data review rather than producing artificial gains.

Defaults: 10 bps commission each way, 10 bps adverse slippage, 15% annual hypothetical short borrow cost accrued once per elapsed calendar day. Short sale proceeds are not spendable; 100% of initial short notional is reserved. Equity includes signed short P/L. Daily 2% loss and peak-to-trough 10% brakes stop entries and queue liquidations. Gaps may exceed planned stop risk. Missing prices remain visibly dated last-observed marks, not live valuations.

## Limits

Rules are uncalibrated research rules, not a demonstrated profitable strategy. Borrow availability, real exchange/broker short eligibility, dividends, corporate-action accounting, queue position and actual market impact are not established by this simulator. No official holiday calendar is inferred: absence of a fresh trading bar prevents fills. The example runner uses explicitly synthetic prices, never mixes its records with forward trading and is not historical performance.

## Verification

Unit/API tests cover account isolation and persistence, all four sides, fees and slippage, short collateral and borrow costs, planned size/exposure limits, decision/fill ordering, duplicate/stale/invalid/weekend bars, gap stops, stop-first ambiguity, daily risk brakes, pause races, fallback/partial universe rejection and exclusion of today's open daily bar. UI tests cover routing, escaped records, control labels and header-only account tokens.

## V27.1 scan scheduling

The 60-second delay after every 20-symbol packet was removed. One scan worker continues unfinished packets on the next scheduler pass (about one second), then rests for ten minutes after a complete scan. Failed data requests back off for 30 seconds. A separate risk worker checks accounts on a 30-second target cadence; slow daily downloads cannot block that worker. Provider/network latency can still delay individual reads. Existing ledgers migrate without resetting cash, orders or positions.

Normal UI scans use at most two concurrent packets. Both normal and automatic scans share copied per-symbol one-year daily OHLCV snapshots for ten minutes, coalesce duplicate in-flight requests and bound provider download concurrency. Empty downloads have a shorter retry cache. Pre-close snapshots expire at the existing 18:20 daily-bar cutoff; the automatic engine still removes open bars. Copy isolation and original fetch timestamps prevent one consumer from modifying or relabelling another consumer's data. UI status shows last packet time and completed scan duration.

On ephemeral web hosting, a redeploy can remove server account files. An existing browser token then receives an explicit missing-account message. The user can choose to create a new paused account; the application never silently resets cash or replaces the account. This does not restore lost history. Desktop account files remain in the application data directory.
