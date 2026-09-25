# BIST AI Terminal Desktop 5.1

Bu sürüm web sitesinden bağımsız olarak bilgisayara kurulur. Arayüz Electron içinde açılır; FastAPI/Python motoru uygulamanın kendi içinde paketlidir ve yalnızca `127.0.0.1` üzerinde çalışır. Render kullanılmaz.

## Üretilen kurulum dosyaları

- Windows 64-bit: `BIST-AI-Terminal-Setup-5.1.0-x64.exe`
- macOS Intel: `BIST-AI-Terminal-5.1.0-x64.dmg`
- macOS Apple Silicon: `BIST-AI-Terminal-5.1.0-arm64.dmg`

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
