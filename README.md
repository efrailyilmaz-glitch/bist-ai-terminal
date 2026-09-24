# BIST AI Quant Research Terminal V4

Borsa İstanbul için teknik, temel, KAP, haber, makro ve portföy-risk katmanlarını birleştiren araştırma terminali.

## V4 ana mimari

### 1) BIST Universe Engine
- KAP BIST şirketleri sayfasından dinamik evren keşfi
- Sabit 20–30 hisselik liste yok
- Şirket kodu, unvan, şehir, denetçi ve KAP şirket profil bağlantısı
- Evren cache ve fallback mekanizması

### 2) Market Data & Technical Engine
- Yahoo Finance üzerinden BIST `.IS` fiyat serileri
- Küçük gruplar halinde dayanıklı tüm-evren tarama
- 15dk / 1sa / 4sa / günlük / haftalık multi-timeframe
- RSI14, Stochastic RSI, MACD 12/26/9
- ADX / +DI / -DI
- Bollinger Bands 20/2
- ATR14
- MFI14
- OBV trend
- EMA20 / EMA50 / EMA200
- XU100 relative strength
- breakout, momentum, hacim ve volatilite ölçümleri

### 3) Structure Engine
- Supertrend 10/3
- Ichimoku Tenkan/Kijun ve cloud sınırları
- RSI ve MACD bullish/bearish divergence
- EMA50/EMA200 Golden Cross / Death Cross
- Bollinger squeeze percentile
- Pivot kümeli otomatik destek/direnç
- Setup Radar: Golden Cross, squeeze, divergence, trend alignment

### 4) Short / Long Horizon Research
- Kısa vade: momentum, breakout, hacim, MACD, Stoch RSI, ADX, relative strength
- Uzun vade: EMA200, 3–6 ay momentum, relative strength, trend gücü ve volatilite
- Alpha, risk, smart-money proxy ve anomaly skorları
- Model gerekçeleri ekranda görünür

### 5) Fundamental Engine
- Yahoo fundamentals üzerinden talep üzerine veri
- Value: F/K, PD/DD, FD/FAVÖK, F/S, FCF yield
- Quality: ROE, ROA, marjlar, serbest nakit akışı, FCF dönüşümü
- Growth: gelir ve kâr büyümesi
- Balance Sheet: borç/özsermaye, cari oran, nakit-borç yapısı
- Shareholder Return: temettü ve payout
- Finansal şirketler için ayrı faktör modeli; bankalar sanayi şirketi gibi FD/FAVÖK/cari oranla puanlanmaz
- Veri kapsam yüzdesi
- TTM gelir, net kâr, FCF, işletme nakit akışı, net borç ve cash-conversion
- Çeyreklik finansal özet
- Analist hedefi yalnız referans olarak gösterilir; research score'a karıştırılmaz

### 6) Factor Lab & Sector Comparison
- Value / Quality / Growth / Balance / Shareholder ayrı skorları
- Fundamental composite
- Yüklenen örneklem içinde sektör yüzdelik karşılaştırması
- Sektör faktör özet tablosu
- Tam sektör konsensüsü olmadığı açıkça etiketlenir

### 7) KAP Engine
- KAP şirket profili, sektör, pazar, endeksler ve beklenen rapor takvimi
- Kamuya açık KAP aramasından olay eşleştirme
- Olay sınıflandırması: sözleşme, yatırım, geri alım/temettü, sermaye aksiyonları, pay işlemleri, hukuki/operasyonel/finansman riskleri
- Sentiment ve materiality ayrı gösterilir
- Lisanslı gerçek-zamanlı KAP REST verisi varmış gibi sahte akış üretilmez

### 8) News Sentiment
- Google News RSS başlık akışı
- Türkçe finans anahtar kelime sentiment'i
- Yalnız başlık analizi olduğu açıkça belirtilir; makale gövdesi analiz edilmiş gibi sunulmaz

### 9) V4 Research Engine
- Teknik + temel + KAP + haber + global makro bileşimi
- Ayrı kısa ve uzun vade araştırma skorları
- Veri-kapsam/confidence skoru
- Güçlü taraflar ve kırmızı bayraklar
- Yüksek risk/anomali cezası
- Veri yoksa N/A / düşük confidence; uydurma nötr veriyle güven yükseltilmez

### 10) Portfolio Risk Lab
- Model araştırma sepeti
- 1 yıllık tarihsel korelasyon matrisi
- XU100 beta
- yıllık volatilite
- maksimum drawdown
- risk katkısı
- çeşitlendirme skoru
- eşit-ağırlık proxy açıkça etiketlenir

### 11) TradingView-style Chart
TradingView Lightweight Charts:
- candlestick + volume
- EMA20/50/200
- Bollinger
- Supertrend
- Ichimoku
- otomatik S/R
- RSI / Stoch RSI pane
- MACD pane
- göstergeleri tek tek aç/kapatma

### 12) Productivity
- Browser-local Watchlist
- tüm tarama CSV export
- KAP/haber bağlantılarından kaynağa gitme
- GitHub CI: Python compile, Node syntax ve research smoke test
- Render deploy-on-commit

## Veri dürüstlüğü

Terminal şu durumları birbirinden ayırır:
- LIVE / YAHOO
- PARTIAL / YAHOO
- CACHE
- NO DATA / N/A

Aşağıdaki veriler uygun lisanslı kaynak olmadan üretilmez:
- gerçek Level-2 order book
- tick-by-tick kurumsal feed
- gerçek takas/saklama/fon akışı
- lisanslı eşzamanlı KAP REST feed
- gerçek broker emir yürütme

Smart-money ve anomaly göstergeleri fiyat/hacim tabanlı proxy'dir; yasa dışı manipülasyon tespiti iddiası değildir.

## Çalıştırma

```bash
pip install -r requirements.txt
bash run.sh
```

Health:
```
/health
```

## Deployment

`render.yaml` bağlı `main` branch commitlerinde otomatik deploy için hazırlanmıştır.

## Uyarı

Bu uygulama nicel ve temel araştırma aracıdır. Model skorları ve araştırma adayları gelecekteki performansı garanti etmez ve kişiye özel yatırım tavsiyesi değildir.
