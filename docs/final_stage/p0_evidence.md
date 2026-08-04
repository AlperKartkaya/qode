# P0 başlangıç ve kapı kanıtı

- **Tarih:** 2026-08-04
- **Git HEAD:** `be5ea87b0882e8e5846578ae47fa604082fded6b`
- **Host Python:** `Python 3.14.0`
- **Docker CLI:** kurulu; daemon çalışmıyor (`Cannot connect to the Docker daemon`)
- **GPU:** repo/host komut yüzeyinden doğrulanmadı; Docker GPU smoke'u daemon kapalı olduğu için çalıştırılamadı
- **ffmpeg/ffprobe:** host PATH üzerinde yok
- **Yerel model weight'i:** `.pt`, `.pth` veya `.onnx` bulunmadı

## Doğrulamalar

- Python testleri: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
  sonucu P0 baseline düzeltmelerinden sonra **49/49 OK**; P1 testleriyle toplam **61/61 OK**.
- Android: `(cd apps/android && ./gradlew :app:assembleDebug)` tamamlandı; yaklaşık 19 MB
  debug APK üretildi.
- Backend: FastAPI `TestClient` ile `GET /health` **HTTP 200** ve
  `{ "status": "ok" }` döndürdü.
- Backend testleri: `backend/venv/bin/python -m pytest -q` sonucu **13 passed**;
  mevcut Starlette/httpx deprecation uyarısı P5 dependency incelemesine bırakıldı.
- HLS master erişilebilir. 1080p (1920x1080, 9,155,202 bps) ve 240p
  (426x240, 289,282 bps) varyantlarının her biri 56 segment ve toplam
  113.92 saniye raporladı.
- Kanonik dosyaların SHA256 değerleri `docs/final_stage/source_inventory.json`
  içinde kayıtlıdır; staging adları kaldırıldı.

## P0 dış kapıları

Credential/SIM/VM ve gerçek Android cihaz HLS->MP4 kanıtı kod deposunda mevcut
olmadığından `docs/final_stage/open_questions.md` içinde owner ve son karar kapısı
ile tutulur. Bu eksikler P1 veri adaptasyonunu engellemez; P5/P6 gerçek entegrasyon
kapılarını engeller.
