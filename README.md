# BIST AI Quant Research Terminal V18

Borsa İstanbul için teknik, temel, KAP/haber, nicel doğrulama, risk, dönemsel davranış ve masaüstü sürekli taramayı tek uygulamada birleştiren araştırma terminali.

## Ana motorlar
- Tüm BIST tarama: kısa/uzun skor, RSI/Stoch/MACD, ADX, MFI, Supertrend, Ichimoku, relative strength.
- Opportunity Radar + Investment Committee + hedef/stop/dip bölgesi Decision Levels.
- Smart Money / Pre-Markup / Distribution: OHLCV tabanlı davranış proxy’leri; gerçek takas/Level-2 değildir.
- Weekly Reversal Radar: 5 yıllık haftalık RSI dip dönüşü + Stoch bullish cross + MACD histogram dönüşü; EMA20, ADX/DI, hacim ve XU100 RS teyidi.
- Cycle & Seasonality Radar: 10 yıllık mevsimsellik ve tekrar düzenliliği; otokorelasyon yön değil düzenlilik ölçüsü olarak kullanılır.
- Experience Lab: canlı oluşan sinyallerin 5/20/60 gün sonraki XU100 excess performansını prospective olarak kaydeder.
- Pro Toolkit, Peer Comparison, RRG-style relative rotation, risk intelligence, seasonality, factor/fundamental, event study.
- Strategy Lab: maliyet/slippage, walk-forward ve Monte Carlo.
- Paper Execution Center: kill switch, emir/pozisyon limiti, günlük gerçekleşmiş zarar limiti ve paper P&L; gerçek broker emri resmi API doğrulanana kadar kapalı.
- Always-On Supervisor: masaüstü/tray açıkken fırsat, Smart Money, Cycle ve Weekly taramalarını arka planda yürütür.
- System Audit: kritik motorların çalışma durumu ve tam-evren tarama kapsamını gösterir.

## Veri ve dürüstlük
- Yahoo fiyat katmanı **DELAYED / YAHOO** olarak etiketlenir; lisanslı gerçek zamanlı BIST feed’i değildir.
- KAP public-page katmanı lisanslı real-time REST dağıtımı değildir.
- Smart Money/anomali belirli kişi veya kurumun işlem yaptığını kanıtlamaz.
- Mevsimsellik, backtest, historical hit-rate ve model hedefleri gelecek sonucu garanti etmez.
- Current-universe tarihsel analizleri survivorship bias içerebilir.
- TMS/TAS 29 ve sektör farklılıkları finansal oran karşılaştırmasını etkileyebilir.
- Direct broker execution yalnız belgelenmiş resmi entegrasyon ile açılmalıdır.

## Masaüstü
Windows x64, Intel Mac x64 ve Apple Silicon arm64 installer’ları GitHub Actions ile üretilir. Ana pencere kapatıldığında uygulama tray’de çalışmaya devam eder; bilgisayar uyku/kapalı durumdaysa yerel tarama çalışmaz.

## Local
```bash
pip install -r requirements.txt
bash run.sh
```

Health: `/health`  
System Audit: `/api/system-audit`  
Data Health: `/api/data-health`

## Disclaimer
Model çıktıları araştırma amaçlıdır; kişiye özel yatırım tavsiyesi veya garanti edilmiş al/sat talimatı değildir.
