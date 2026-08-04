# ADR-0001: Final mobil ve backend sınırı

- **Durum:** Kabul edildi
- **Tarih:** 2026-08-04
- **Karar sahipliği:** QoDe mobil ve backend geliştirme sahipleri

## Bağlam

Repo incelemesinde iki mobil yüzey bulundu. `apps/android/` native Kotlin/Compose,
Media3 ve Retrofit kullanan, Gradle wrapper ile build edilen güncel final adayıdır.
`apps/mobile/` ise Expo/React Native prototipidir. Ayrıca planın varsaydığı boş
`services/api/` yerine `backend/` altında çalışan FastAPI uygulaması, Open Gateway
client'ı, upload/job akışı ve container runner zaten bulunmaktadır.

İkinci bir mobil uygulama ya da ikinci bir backend üretmek; sözleşme ayrışması,
çift bakım ve final gününde yanlış artefact çalıştırılması riski yaratır.

## Karar

1. Final mobil ürününün kanonik yüzeyi **`apps/android/`** olacaktır.
2. `apps/mobile/` yalnız legacy UX/prototip referansı olarak tutulacak; final APK
   veya final sözleşme authority'si olmayacaktır.
3. Final demo backend'inin kanonik yüzeyi **`backend/`** olacaktır. P5 bu uygulamayı
   güvenlik ve gerçek Open Gateway sözleşmeleri bakımından sertleştirecektir.
4. `services/api/` ikinci server olmayacak; mevcut placeholder sonraki aşamada
   kanonik `backend/` yüzeyine yönlendiren uyumluluk dokümanına dönüştürülecektir.
5. `src/smart_road_safety/local_api/` geliştirme ve contract smoke yüzeyi olarak
   kalacak; production upload/job authority'si olmayacaktır.
6. AI competition image; OAuth credential, mobil session veya backend state
   taşımadan `/app/data/input/video.mp4` -> `/app/data/output/results.json`
   sınırını koruyacaktır.

## Kanıt

- `(cd apps/android && ./gradlew :app:assembleDebug)` tamamlandı; debug APK:
  `apps/android/app/build/outputs/apk/debug/app-debug.apk` (yaklaşık 19 MB).
- `backend/venv/bin/python` ve FastAPI `TestClient` ile `GET /health` sonucu:
  HTTP 200, `{ "status": "ok" }`.
- Repo içinde ayrıca bağlanabilir harici mobil/backend repo referansı veya build
  artefact kimliği bulunmadı.

## Sonuçlar ve takip

- P5 ve P6 yalnız yukarıdaki kanonik yüzeylerde uygulanacaktır.
- Mevcut backend'in istemciden token kabul eden ve mock/fallback yolları P5'te
  ayrıca ele alınmalıdır; bu ADR bunları güvenli kabul etmez.
- Gerçek Android cihazda HLS kayıt/remux smoke'u henüz kanıtlanmadı ve P6 öncesi
  dış/cihaz bağımlı kapı olarak açık kalır.
