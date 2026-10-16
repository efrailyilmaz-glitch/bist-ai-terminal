# V26 — TradingView topluluk göstergeleri (16.10.2026)

## Seçim ve kapsam

Amaçlı kısa liste, tüm TradingView'in kapsamlı/popülerlik sıralaması değildir. Görünen yuvarlanmış etkileşimler arama motorunun yaklaşık üç haftalık önbelleğindendir; bugün ölçülmüş kesin beğeni veya aktif kullanım sayısı değildir. Etkileşim yatırım başarısı kanıtlamaz.

| Yayın / yazar | Yaklaşık etkileşim | Karar |
|---|---:|---|
| Smart Money Concepts / LuxAlgo | 168.200 | Araştırma: eksiksiz port yok; mevcut Smart Money modülü bu script değildir |
| Squeeze Momentum / LazyBear | 116.300 | Bağımsız formül uyarlaması eklendi |
| WaveTrend / LazyBear | 60.800 | Bağımsız formül uyarlaması eklendi |
| UT Bot Alerts / QuantNomad | 58.500 | Normal kapanış kullanan bağımsız ATR takip uyarlaması eklendi |
| Lorentzian Classification / jdehorty | 36.400 | Araştırma: model etiketleri, sürümleri, BIST kronolojik testi gerekli |
| Nadaraya-Watson Envelope / LuxAlgo | 34.500 | Araştırma: yeniden boyayan varsayılan yöntem sinyale eklenmedi |
| Chandelier Exit / everget | 29.100 | Kapanış ekstremli bağımsız takip formülü eklendi |
| SuperTrend / Kıvanç Özbilgiç | Ölçülmedi | Standart Supertrend zaten mevcut; bu yayının birebir portu değil |
| OTT / Anıl Özekşi, Kıvanç Özbilgiç | Ölçülmedi | Araştırma: farklı ortalama türleri ve VAR başlangıcı doğrulanmalı |
| Choppiness Index / E. W. Dreiss | Sıralama yapılmadı | Kendi yöntem seçimimiz: yataylık bağlamı eklendi |

## Eklenen işlevler

- Hisse grafiğinde ayrı WaveTrend, Squeeze Momentum ve CHOP panelleri; Chandelier ve UT takip çizgileri fiyat üzerinde. Var olan RSI/Stoch ve MACD panel düzeni korunur.
- Topluluk Göstergeleri sayfasında koşullu günlük tarama, kapanmış bar tarihi ve CSV dışa aktarım.
- Hisse Tarama sayfasında yeni alanlar ve hazır taramalar.
- Mevcut bildirim merkezine uygun, güncel ve kontrolü temiz kapanmış bar olayları. Yenileme yeni olay üretmez; mevcut teknik bildirim deduplikasyonu kullanılır. Tarama gözlemidir, arka planda yeni ayrı motor veya emir değildir.
- Beş yıllık veride dört sabit giriş koşulunun betimsel karşılaştırması. Sonraki açılışta giriş, 10 bar sonra açılışta çıkış, örtüşmeyen işlemler; ilk %65 / son %35 ayrı, toplam maliyet açık. XU100 kıyası, limit fiyat ve stop gerçekleşmesi modellenmez. Son dönem gerçek ileri test değildir; sonuçlardan otomatik en iyi gösterge seçilmez.

## Parametreler ve hesap farkları

Uygulama Pine runtime içermez. Kaynak kodu kopyalanmadı; bilinen matematiksel yöntemler bağımsız Python koduyla uygulandı. Yazarlar ve kavram kökenleri katalogda belirtilir. TradingView ile bar bar değer eşitliği doğrulanmadı.

- WaveTrend: HLC3; EMA10 kanal ve mutlak sapma; 0,015 normalizasyon; EMA21; SMA4 sinyal. En az 50 bar ısınma. Sıfır sapma sıfır sinyal olarak doldurulmaz.
- Squeeze: BB SMA20 ± 2 × nüfus standart sapması; KC SMA20 ± 1,5 × SMA20 true range; 20 bar lineer regresyon momentumu. BB çarpanı bağımsız 2'dir. Eski Pine sürümlerinin çarpan farklarıyla tam eşitlik iddiası yok.
- Chandelier: 22 bar kapanış ekstremi ± 3 × ATR22. Wilder ATR, ilk 22 TR'nin ortalamasıyla başlar; bantlar geçmiş kapanışla taşınır. İlk yön yalnız başlangıç durumudur; yeni kesişim sayılmaz.
- UT: ATR10 ×1; normal kapanış, ilk stop kapanış − ATR. Heikin Ashi seçeneği yok. Başlangıç farkı nedeniyle birebir Pine portu değildir.
- CHOP14: 100 × log10(sum(TR14)/(highest(high14)−lowest(low14))) / log10(14). Sıfır aralık tanımsızdır. 61,8 üstü yataylık, 38,2 altı trend yapısı; yön söylemez.

Yalnız günlük ve haftalık barlar desteklenir. Yeni hesaplarda açık günlük bar Türkiye saati 18:20'ye kadar, haftalık bar cuma 18:20'ye kadar dışarıda kalır. Tatil/erken kapanış takvimi bağlı değildir: kesim muhafazakârdır. Gelecekte kapanacak bar kullanılmaz. Fiyat sağlayıcısının geçmiş veriyi değiştirmesi ve kurumsal işlemler tarihsel sonuçları değiştirebilir; nedensellik testi bunu engellemez. Grafik diğer mevcut göstergelerde açık bar gösterebilir; topluluk çizgileri son teyitli barda biter.

Yukarı dönüşler tek başına alım değildir. Birleşik filtre: UT veya Chandelier yeni yukarı; CHOP <61,8; kapanmış bar hacmi önceki 20 bar ortalamasının en az 1,2 katı. Bu birleşim deneysel, kalibre edilmemiştir. Mevcut alfa skorları bu yeni yöntemlerle yükseltilmez.

## Ticari olmayan GitHub kapsamı

Kullanıcının ticari olmayan kullanım tercihi kaydedildi. Önceki 14 aday (QuantStats, PyPortfolioOpt, Alibi Detect, borsapy, OpenBB, Darts, Ghostfolio, FinGPT, FinBERT, Qlib, Ollama, Backtesting.py, vectorbt, Optuna) değerlendirme kapsamında. FinBERT ticari olmayan kullanım nedeniyle artık otomatik dışlanmaz; İngilizce modelin Türkçe KAP başarısı, model ve eğitim verisi koşulları ayrı kalır. Ücretsiz kişisel kullanım, kodun yeniden dağıtım yükümlülüklerini veya borsa verisi haklarını kendiliğinden kaldırmaz. Bu sürümde bu paketler kurulmadı; mevcut bağımlılıklarla gösterge işlevleri eklendi.

## Birincil kaynaklar

- https://www.tradingview.com/script/2KE8wTuF-Indicator-WaveTrend-Oscillator-WT/
- https://www.tradingview.com/script/nqQ1DT5a-Squeeze-Momentum-Indicator-LazyBear/
- https://www.tradingview.com/script/n8ss8BID-UT-Bot-Alerts/
- https://www.tradingview.com/script/AqXxNS7j-Chandelier-Exit-everget/
- https://www.tradingview.com/support/solutions/43000773013-chandelier-exit/
- https://www.tradingview.com/support/solutions/43000501980-choppiness-index-chop/
- https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/
- https://www.tradingview.com/script/WhBzgfDu-Machine-Learning-Lorentzian-Classification/
- https://www.tradingview.com/script/Iko0E2kL-Nadaraya-Watson-Envelope-LuxAlgo/
- https://www.tradingview.com/script/zVhoDQME/
- https://www.tradingview.com/pine-script-docs/concepts/repainting/
- https://www.tradingview.com/house-rules/
