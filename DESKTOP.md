# BIST AI Terminal Desktop 126.0

Bu sürüm web sitesinden bağımsız olarak bilgisayara kurulur. Arayüz Electron içinde açılır; FastAPI/Python motoru uygulamanın kendi içinde paketlidir ve yalnızca `127.0.0.1` üzerinde çalışır. Render kullanılmaz.

## Üretilen kurulum dosyaları

- Windows 64-bit: `BIST-AI-Terminal-Setup-126.0.0-x64.exe`
- macOS Intel: `BIST-AI-Terminal-126.0.0-x64.dmg`
- macOS Apple Silicon: `BIST-AI-Terminal-126.0.0-arm64.dmg`

## Kurulum davranışı

### Windows
- Klasik NSIS kurulum sihirbazı
- Kurulum klasörü seçilebilir
- Masaüstü kısayolu oluşturulur
- Başlat menüsü kısayolu oluşturulur
- Uygulama kaldırılırken yerel kullanıcı verileri otomatik silinmez

### macOS
- Standart DMG penceresi
- Uygulama Applications klasörüne sürüklenerek kurulur
- Intel ve Apple Silicon için native ayrı build

## Yerel veri kökü

Electron, backend'e `BIST_AI_DATA_DIR=<userData>/data` verir. Experience ledger, model registry, paper/robot state, radar state ve governance verileri bu yazılabilir kökte tutulur.

## Yerel çalışma

Uygulama açılışında:
1. Boş bir localhost portu seçilir.
2. Paketlenmiş Python motoru gizli olarak başlatılır.
3. `/health` yanıtı beklenir.
4. Masaüstü pencere yerel terminali açar.
5. Uygulama kapanınca Python motoru da kapatılır.

Yahoo/KAP/haber gibi canlı dış kaynaklar için internet bağlantısı gerekir. Hesaplama, grafik, tarama ve araştırma motoru bilgisayar üzerinde çalışır.

## Güvenlik

- Node integration kapalı
- Electron context isolation açık
- Electron sandbox açık
- Dış bağlantılar sistem tarayıcısında açılır
- Backend yalnızca `127.0.0.1` adresine bind edilir
- Web uygulamasındaki security headers korunur

## Signing / Notarization

Build pipeline sertifika olmadan da installer üretir.

Kurumsal dağıtım için aşağıdaki GitHub Secrets tanımlanırsa imzalama otomatik kullanılır:
- Windows: `WIN_CSC_LINK`, `WIN_CSC_KEY_PASSWORD`
- macOS: `MAC_CSC_LINK`, `MAC_CSC_KEY_PASSWORD`
- Apple notarization: `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID`

Sertifika yoksa Windows SmartScreen veya macOS Gatekeeper ilk açılışta uyarı gösterebilir. Bu, uygulamanın çalışmasına değil imzalanmamış olmasına ilişkindir.

## Otomatik build

`.github/workflows/desktop-build.yml`:
- Windows x64 runner üzerinde EXE installer
- macOS Intel runner üzerinde x64 DMG
- macOS Apple Silicon runner üzerinde arm64 DMG
- PyInstaller backend smoke test
- Electron Builder packaging
- GitHub Actions artifact upload

`desktop-v*` etiketiyle tetiklenen build ayrıca installer dosyalarını GitHub Release'e ekler.

## V19 araştırma ve gezinme

Hisse tıklamaları tarayıcıda yeni sekme açar. Mac masaüstü uygulamasında yerel sekme desteği kullanılır; Windows masaüstünde ayrı analiz penceresi açılır. Kaynak liste korunur. Her sayfada Geri dön düğmesi bulunur. Paylaşılabilir URL hisse, sayfa ve grafik periyodunu içerir.

Olasılık Laboratuvarı 10 yıllık fiyat geçmişinden 5/20/60 işlem günü için benzer dönem senaryoları üretir. 9 nedensel teknik özellik, örtüşmeyen analoglar, 5 bar embargo ve geçmişe dönük zaman sıralı Brier testi kullanır. Kanıt yetersizse karar üretmez. Model yalnızca teknik tarihsel araştırmadır; gerçek işlem, emir defteri veya kalibre edilmiş gelecek olasılığı değildir.

## V20 Strateji Araştırması

Kaynaklı yedi hipotez ve üç sabit uzun pozisyon kuralı eklendi. Deney kapanış sinyalinden sonraki açılışta başlar; XU100 aynı tarihlerde karşılaştırılır. Maliyet ve iki kat maliyet stresi, zaman sıralı dönem ayrımı, eksik tarih kontrolleri ve hesaplanabilen son işlemler görünürdür. Sonuçlar keşif amaçlıdır; canlı işlem onayı üretilmez.

Eski alfa araştırmasında satır sırası yerine tarih eşleştirmesi kullanılır; 60 günlük örneklerin örtüşmesi kaldırılmıştır. KAP olay getirisinde karşılaştırma başlangıç ve bitiş tarihleri eşleştirilmiştir. Şirket tablosu başlığı artık hisse evrenine girmez.

## V21 Grafik araçları ve yerel simülasyon

Grafik kenarında çizgi, yatay çizgi, üç noktalı paralel kanal, cetvel, renk seçimi, silme ve geri al/yinele bulunur. Çizimler hisse ve zaman dilimine göre bu cihazda saklanır; farklı zaman dilimlerine otomatik taşınmaz.

Grafik altındaki AL, SAT, AÇIĞA SAT ve AÇIĞI KAPAT düğmeleri yalnız yerel simülasyon hesabını değiştirir. 1 milyon TL sanal başlangıç sermayesi, tek yön komisyon ve short için %100 ek teminat varsayımı kullanılır. Hesap eski Execution Center paper hesabından ayrıdır. Gerçek aracı kurum API bağlantısı yoktur; gerçek emir gönderme düğmesi kapalıdır.

Agresif alış, kullanıcının fiyat;lot biçiminde girdiği deneme satış kademelerini düşükten yükseğe tüketir. Hedef toplam lot, alt emir lotu ve üst fiyat zorunludur. Kademe tükenmesi, fiyat/pozisyon/nakit sınırı, 200 alt emir sınırı, Durdur, sayfadan ayrılma veya sekmenin gizlenmesi kalan planı durdurur. Gerçek kademe verisi veya gerçekleşme iddiası yoktur. Birden çok sekmede aynı yerel hesaba yazımlar Web Locks ile sıraya alınır.

Masaüstü yerel adresi yeniden başlatmalarda korunur; çizimler ve grafik simülasyonu aynı cihazdaki uygulama profilinde saklanır. Kayıtlı port kullanımda ise uygulama farklı adrese geçmek yerine hata gösterir.


## V123 paketleme doğrulaması

Installer üretiminden önce sürüm eşleşmesi, Electron sandbox ayarları, loopback backend, icon kaynakları ve paketlenmiş Python backend yolu doğrulanır. Her platform build'i `BUILD-<platform>-<arch>.json` manifesti üretir; manifest installer SHA-256 değerini, dosya boyutunu, Git commit'ini, platform ve mimariyi kaydeder. Release ayrıca `SHA256SUMS.txt` yayınlar.


## Controlled Live Readiness

V126 canlı emir yetkisi açmaz. Forward evidence, research integrity, desktop/runtime, broker sandbox, lisanslı gerçek zamanlı veri ve doğrulanmış resmi broker sözleşmesi ayrı hard gate olarak raporlanır. Tüm gate'ler geçse bile sonuç yalnız manuel entegrasyon/güvenlik incelemesine hazır olunduğunu belirtir.
