# P3–P4 uygulama ve doğrulama kanıtı

**Tarih:** 4 Ağustos 2026  
**Durum:** Kod ve fail-closed sözleşmeler hazır; final asset/GPU/Docker kabulü dış girdiler bekliyor.

## Uygulanan P3 yüzeyleri

- `config/runtime_assets.json` tek machine-readable envanterdir. Kaynak, lisans,
  revision/model sürümü, dosya adı, SHA256 ve beklenen class mapping aynı yerde tutulur.
- Public HF revision'ındaki driver, vehicle type, plate ve teknocan dosyalarının
  SHA256 değerleri sabitlenmiştir. Downloader, upload helper, Docker ve model kartı
  aynı manifestten türetilir.
- Main detector ile offline OCR henüz checksum ile dondurulmamıştır. Vehicle-color
  ve cabin detector (`emniyet_kemeri_ihlali`, `bilgisayar`, üç yolcu koltuğu) henüz
  eğitilip yayımlanmamıştır. Bunlar `external-blocker` olarak görünür ve final
  checker'ı geçemez.
- Final modunda missing/checksum/class mapping hatası inference başlamadan non-zero
  olur. Degraded yol yalnız `development` + açık `--allow-degraded-inference` ile
  seçilebilir; final modunda bu bayrak reddedilir.
- Video pipeline 3–5 FPS aralığında config edilir (default 4 FPS), capture PTS'ini
  kullanır, geri giden PTS'i reddeder ve yalnız metadata yoksa frame/FPS zamanına
  döner.
- Global dedup kaldırıldı. Driver davranışları için persistence, nesne/yolcu için
  visibility transition ve episode gap uygulanır; ayrık tekrarlar korunur.
- `slalom`, tek frame etiketi olarak kabul edilmez; normalize araç track merkezinde
  zaman pencereli yön değişimlerinden üretilir.
- Final prediction, video timeline'dan doğrudan stabil sıralanır. Araç bilgisi yoksa
  sahte sedan/plaka/renk yazılmaz.

## Uygulanan P4 yüzeyleri

- Kanonik image: `teknofest-2026/qode-final:2026.08-p4`.
- Girdi `/app/data/input/video.mp4`, çıktı `/app/data/output/results.json`.
  Başka medya/dosya final modunda açık hatadır.
- JSON geçici dosyada yazılır, tekrar schema validator'dan okunur ve `os.replace`
  ile atomik yayımlanır.
- Runtime network kapalıdır; build yalnız önceden staged ve checksum doğrulanmış
  asset'leri image'a kopyalar. Warning-only download ve `|| true` kaldırılmıştır.
- `config/runtime_environment.json`, amd64 base digest, CUDA, torch/torchvision,
  dependency lock ve schema bilgisini kaydeder. Proje Python alt sınırı, pinned
  Ubuntu 22.04/CUDA runtime'ın Python 3.10 sürümüyle uyumlu olacak şekilde `>=3.10`
  olarak açıkça hizalanmıştır.
- Health/readiness GPU, bütün asset/checksum/class map, writable output, schema
  version ve model warm-up kontrolünü içerir.
- `scripts/benchmark_final_image.py` low/high/mobile vakalarını `--network none`
  ile ayrı temiz mount'larda çalıştırır; wall time, container/GPU memory, writable
  layer size, input/output checksum, exit code ve schema sonucunu kaydeder.
- `scripts/freeze_final_image.py` image Id/RepoDigest/OCI label, tar ve tar SHA256
  kanıtını `out/final_stage/freeze/` altında üretir.

## Doğrulama komutları

```bash
PYTHONPATH=src python3 -m compileall -q src tests main.py scripts
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m smart_road_safety.cli check-runtime-assets \
  --manifest config/runtime_assets.json --asset-root data/weights --mode final
PYTHONPATH=src python3 -m smart_road_safety.cli check-runtime-readiness \
  --manifest config/runtime_assets.json --asset-root data/weights \
  --output-dir out/readiness --allow-cpu --skip-warmup
docker build --platform linux/amd64 -t teknofest-2026/qode-final:2026.08-p4 .
```

Beklenen bugünkü sonuç: compile/test geçer; son üç readiness/build adımı eksik final
asset setini veya Docker daemon yokluğunu açık hata ile gösterir. Bu bir başarı
iddiası değil, sahte/silent fallback'i engelleyen release kapısıdır.

### 4 Ağustos gerçek çıktı özeti

- `compileall`: exit `0`.
- Python: `84 tests`, `OK`.
- Backend: `13 passed`; yalnız mevcut Starlette/httpx deprecation uyarısı.
- Faz 2 manifest checker: `result=pass`, `sample_count=1`, `34` GT event.
- Manifest downloader dört public checkpoint'i indirip SHA256 ile doğruladı. Exit
  `2`, çünkü main detector, vehicle-color, OCR bundle ve cabin detector unfrozen.
- Final main smoke: exit `2`, asset/class inspection hatalarını stderr'e yazdı ve
  önceden bırakılmış `results.json` dosyasını sildi; stale success bırakmadı.
- Docker build: exit `1`, yerel Docker daemon socket'ine bağlanılamadı. Image,
  RepoDigest, tar SHA256 veya Web UI başarısı bu yüzden üretilmiş gibi gösterilmedi.

## Kapanmamış fiziksel kabul kanıtları

1. Main detector için exact revision/dosya/SHA256 ve EasyOCR için detector + `tr`/`en`
   recognizer dosyalarını içeren tekrarlanabilir `easyocr-tr-en.bundle` tar/sidecar/SHA256 sağlanması.
2. Calibrated vehicle-color ve cabin detector checkpoint/class metadata eğitimi.
3. Bütün asset'lerin `data/weights/` altında staging'i ve final class inspection.
4. NVIDIA T4 hedefinde low/high/mobile üç gerçek MP4 benchmark'ı (<10 dakika).
5. Çalışan Docker daemon ile tek image build, offline run ve Web UI koşusu.
6. Freeze artifact/RepoDigest/tar SHA256 kaydı. Bu kanıtlar oluşmadan P3/P4 fiziksel
   kabulü veya competition readiness ilan edilmeyecektir.
