# P1 review kanıtı — P2 öncesi durma noktası

Tarih: **2026-08-04**

## G1 sonuçları

| Kontrol | Sonuç |
| --- | --- |
| `check-manifest data/final_stage/faz2/manifest.json` | `result=pass` |
| `inspect-dataset ... --dataset-root data/final_stage/faz2` | 1 sample, 2 artifact (426x240 ve 1920x1080), 34 GT event |
| `validate-ftr-output .../ground_truth.json` | `result=pass`, `video_id=video.mp4`, `tespit_count=34` |
| HLS canlı probe | İki varyant, varyant başına 56 segment, 113.92 saniye |
| HLS idempotency/checksum negatif testi | Unit test ile iki ardışık `cached`; mismatch açık hata |
| Adapter negatif vakaları | eksik local video, bozuk JSON, duplicate, geçersiz label, negatif ve süre dışı timestamp test edildi |
| Runtime GT sızıntısı araması | `main.py`, backend ve Android'de GT referansı yok; yalnız data adapter'ında bulunuyor |
| Python suite | 61/61 OK |
| Python compileall | başarılı |
| Backend suite | 13 passed, 1 dependency deprecation warning |
| Android debug build | başarılı, yaklaşık 19 MB APK |

## Bilinçli sınırlar

- Manifest iki HLS varyantını `remote` olarak envanterler. Hostta `ffmpeg` ve
  `ffprobe` bulunmadığı için MP4 remux çalıştırması bu makinede `exit=2` ve açık
  prerequisite mesajıyla durdu. `--probe-only` gerçek HLS üzerinde başarılıdır.
- Remux kodu atomik `.partial.mp4`, ffprobe metadata, SHA256, manifest atomik
  güncelleme ve cache mismatch fail davranışını içerir. Gerçek MP4 artefact üretimi
  ffmpeg bulunan final build/CI makinesinde çalıştırılmalıdır.
- Organizer credential/SIM/VM ve gerçek Android cihaz export kanıtları P1 veri
  kapısının dışında, P5/P6 blokları olarak `open_questions.md` içinde kayıtlıdır.
- P2 evaluator kodu özellikle başlatılmadı; bu dosya user review stop noktasıdır.

## Diagnostics availability

`ruff`, `mypy` ve `pyright` host PATH'inde bulunmamaktadır; yeni dependency
eklenmedi. Buna karşılık `compileall`, `git diff --check`, unit/integration testleri,
manifest/GT validator ve canlı HLS probe çalıştırılmıştır.
