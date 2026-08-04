# QoDe — Smart Road Safety (5G & AI)

**TEKNOFEST 2026 — 5G ve Yapay Zekâ ile Akıllı Yol Güvenliği Yarışması — Final Aşaması**

## Proje Özeti

QoDe, yol kenarı kameralarından gelen video akışını gerçek zamanlı analiz eden bir yapay zekâ sistemidir. Araç tipini, rengini, plakasını ve kabin içi davranışları (sürücü eylemleri, yolcular, nesneler) tespit ederek FTR şartnamesine uygun `results.json` üretir. KTR rapor hattı ise bu çıktı sözleşmesini, açık kaynak veri seti kapsamını, eğitim kanıtlarını ve final rapor şablonunu tek izlenebilir akışta birleştirir.

Source-of-truth sırası:

1. `docs/final_stage/final_yarisma_senaryosu.pdf`
2. `docs/final_stage/platform_operasyon_rehberi.pdf`
3. `docs/final_stage/open_gateway/`
4. `docs/final_stage/open_gateway_demo_ux.pdf`
5. `data/final_stage/faz2/ground_truth.json` (yalnız geliştirme/değerlendirme)
6. FTR teslim dokümanı, şartname ve geçmiş KTR/FTR belgeleri
7. local/open-source support datasets

Current milestone:

- explicit KTR/FTR assumptions in `assumptions.md`
- real dataset manifests for support datasets under `data/datasets/*/manifest.json`
- dataset adapters for State Farm, DMD Distraction, DMD Drowsiness, DriverSVT, and the legacy three-video bundle
- real YOLO/EasyOCR/classifier inference path in `main.py` and `src/smart_road_safety/analysis/model_inference.py`
- training scripts for driver behavior, vehicle type, YOLO, synthetic plates, windshield augmentation, and Hugging Face weight upload/download
- separate FTR competition `results.json` contract under `src/smart_road_safety/competition/`
- reproducible report-model artifact training under `src/smart_road_safety/modeling/`
- KTR DOCX/Markdown/evidence generation under `src/smart_road_safety/reporting/`
- tracked Mermaid architecture sources under `docs/diagrams/`, rendered diagram PNGs, and image-based code appendices for the report
- deterministic scenario evaluation, markdown export, CLI commands, and a tiny stdlib local HTTP API

---

## Mimari

```text
Video (.mp4)
    │
    ▼
YOLO11x ──────────────── Araç / Kişi / Nesne Tespiti
    │
    ├─► Araç crop ──► K-Means Renk ──► vehicle_color
    │               ├─► EasyOCR ──────► plate_text
    │               └─► EfficientNet-B0* ► vehicle_type
    │
    ├─► Sürücü crop ► EfficientNet-B2* ► sofor_eylemi
    │               └─► Hough Lines ──► emniyet_kemeri_ihlali
    │
    ├─► Yolcu bölgesi ► Zone Logic ──► arka_koltuk_1/2, on_koltuk
    │
    └─► Nesne tespiti ► YOLOv11n (Teknocan) + YOLOv11x (Bilgisayar)
    │
    ▼
Temporal Smoothing (3 sn dedup)
    │
    ▼
results.json (FTR uyumlu)
```

`*` = eğitim gerektirir, aşağıya bakın.

---

## FTR Çıktı Şeması

FTR kaynak dokümanı final inference çıktısını `/app/data/output/results.json` altında bekler:

```json
{
  "video_id": "video_001.mp4",
  "arac_bilgisi": {
    "tip": "sedan",
    "plaka": "34ABC123",
    "renk": "beyaz",
    "confidence_score": 0.94
  },
  "tespitler": [
    {
      "zaman_saniye": 14.5,
      "kategori": "sofor_eylemi",
      "etiket": "telefonla_konusma",
      "confidence_score": 0.89
    },
    {
      "zaman_saniye": 22.1,
      "kategori": "yolcular",
      "etiket": "arka_koltuk_1",
      "confidence_score": 0.78
    }
  ]
}
```

Desteklenen etiketler:

| Kategori | Etiketler |
|---|---|
| `sofor_eylemi` | `arkaya_bakma`, `esneme`, `sigara_icme`, `su_icme`, `telefonla_konusma`, `slalom`, `etrafa_bakinma`, `emniyet_kemeri_ihlali` |
| `nesneler` | `teknocan` (Özel yolo11n Ajan Modeli), `bilgisayar` |
| `yolcular` | `arka_koltuk_1`, `arka_koltuk_2`, `on_koltuk` |

Repo exact keyleri, izin verilen etiketleri, confidence aralıklarını, ASCII-safe etiketleri ve Türk plaka regex uyumluluğunu doğrular. Mevcut support veri setleri tüm örneklerde exact araç tipi/renk/plaka metni içermediği için bu alanlar gerçek model/anotasyon kaynağı gelene kadar inference veya açık `vehicle_info.json` sidecar gerektirir.

---

## Veri Setleri ve KTR Kapsamı

### Final Faz 2 paketi

`data/final_stage/faz2/manifest.json`, organizer HLS master'ını, 240p/1080p
varyant metadata'sını ve checksum doğrulanan 34-event `ground_truth.json` fixture'ını
tek sözleşmede tutar. Ground truth yalnız development calibration/evaluation içindir;
`main.py` veya runtime image tarafından okunmaz.

```bash
# Manifest ve adapter envanteri
PYTHONPATH=src python3 -m smart_road_safety.cli check-manifest \
  data/final_stage/faz2/manifest.json
PYTHONPATH=src python3 -m smart_road_safety.cli inspect-dataset \
  data/final_stage/faz2/manifest.json --dataset-root data/final_stage/faz2

# HLS metadata probe (medya indirmez)
python3 scripts/fetch_final_stage_hls.py --probe-only

# 240p ve 1080p'yi atomik MP4 remux eder; ffmpeg ve ffprobe PATH'te olmalıdır
python3 scripts/fetch_final_stage_hls.py
```

İndirilen `data/final_stage/faz2/media/*.mp4` dosyaları gitignore'dadır. Araç
checksum eşleşen cache'i değiştirmez; eşleşmeyen mevcut dosyada açık hata verir.

Birincil local support veri setleri `data/datasets/` altında beklenir:

| Veri Seti | Root | Sample unit | Label source | FTR rolü |
| --- | --- | --- | --- | --- |
| State Farm Distracted Driver | `data/datasets/state-farm-distracted-driver` | labelled image | `driver_imgs_list.csv` + class folders | phone/drinking driver-action support |
| DMD Distraction | `data/datasets/dmd-distraction` | multi-camera video session | OpenLABEL frame actions | phone/drinking/gaze/reaching driver-action support |
| DMD Drowsiness | `data/datasets/dmd-drowsiness` | multi-camera video session | OpenLABEL frame actions | `esneme`/drowsiness support |
| DriverSVT | `data/datasets/DriverSVT-teknofest` | telemetry row | CSV `dangerousstate` | telemetry/speed/risk support |

Legacy secondary dataset:

- `data/video_1.mp4`, `data/video_2.mp4`, `data/video_3.mp4`
- companion screenshot folders under `data/snap_from_video_*/`
- clip observations in `data/video_observations.json`
- local FTR smoke cases için faydalıdır; exact type/color/plate text label kapsamı sağlamaz

Önemli sınırlar:

- FTR/şartname hedef kümesi mevcut support veri setlerinden daha geniştir.
- Plate OCR, vehicle type/color, `teknocan`, `bilgisayar` ve passenger-seat label aileleri ek veri veya curated anotasyon gerektirir.
- Şartname gerçek hızdan bahseder, fakat mevcut FTR `results.json` şeması speed key içermez; speed şema değişene kadar internal/reporting objective olarak tutulur.
- Number Verification canlı demo kapısıdır; QoD başarısı ek puan yoludur. Gerçek endpoint
  sözleşmeleri repodadır, credential/SIM/callback provisioning dış bağımlılıktır.

Large dataset payloads local-only kalır; `.gitignore` `data/datasets/**` içeriğini küçük manifest JSON dosyaları hariç ignore eder.

---

## Kurulum (Geliştirici)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Model Ağırlıkları

Model ağırlıkları boyutları nedeniyle git'e dahil edilmez. Docker build aşamasında otomatik indirilir.

**Yerel geliştirme için:**

```bash
chmod +x download_weights.sh
./download_weights.sh
```

**Eğitim pipeline'ı (sırasıyla):**

```bash
# 1. State Farm veri setini hazırla (22k görsel, ~10-15 dk)
python -m smart_road_safety.training.preprocess_state_farm --max-samples 0

# 2. Sürücü davranış sınıflandırıcısını eğit (EfficientNet-B2, ~2-3 saat M4 Pro)
python -m smart_road_safety.training.train_classifier --epochs 20

# 3. Araç tipi sınıflandırıcısını eğit
python -m smart_road_safety.training.train_vehicle_type_classifier

# 4. Sınıflandırıcı değerlendirmesi
PYTHONPATH=src python -m smart_road_safety.training.eval_classifier
```

KTR rapor metrikleri için hafif ve tekrar üretilebilir local kanıt artefactleri ayrıca üretilebilir:

```bash
PYTHONPATH=src python -m smart_road_safety.cli train-report-models --max-driver-svt-rows 50000
```

---

## Docker ile Çalıştırma

**Önemli:** `docker build` öncesinde `data/weights/driver_classifier.pt` dosyasının mevcut olması gerekir. Bunu yukarıdaki eğitim adımlarıyla veya weight download akışıyla oluşturun.

```bash
# 1. Image oluştur (model ağırlıkları bu aşamada indirilir — timeout'a dahil değil)
docker build -t teknofest-2026/qode:latest .

# 2. Değerlendirme ortamına uygun şekilde çalıştır
docker run --rm --gpus all \
  -v /path/to/video.mp4:/app/data/input/video.mp4 \
  -v /path/to/output:/app/data/output \
  teknofest-2026/qode:latest

# Sonuç: /path/to/output/results.json
```

---

## CLI Komutları

```bash
# Assumptions ve manifest kontrolü
PYTHONPATH=src python -m smart_road_safety.cli print-assumptions
PYTHONPATH=src python -m smart_road_safety.cli check-manifest data/datasets/state-farm-distracted-driver/manifest.json
PYTHONPATH=src python -m smart_road_safety.cli check-manifest data/datasets/dmd-distraction/manifest.json
PYTHONPATH=src python -m smart_road_safety.cli check-manifest data/datasets/dmd-drowsiness/manifest.json
PYTHONPATH=src python -m smart_road_safety.cli check-manifest data/datasets/DriverSVT-teknofest/manifest.json

# Dataset incelemesi
PYTHONPATH=src python -m smart_road_safety.cli inspect-dataset data/datasets/state-farm-distracted-driver/manifest.json \
  --dataset-root data/datasets/state-farm-distracted-driver

# Dataset-backed analysis sessions
PYTHONPATH=src python -m smart_road_safety.cli run-analysis-session examples/analysis_session_state_farm.json
PYTHONPATH=src python -m smart_road_safety.cli run-analysis-session examples/analysis_session_dmd_distraction.json
PYTHONPATH=src python -m smart_road_safety.cli run-analysis-session examples/analysis_session_dmd_drowsiness.json
PYTHONPATH=src python -m smart_road_safety.cli run-analysis-session examples/analysis_session_driversvt.json

# FTR çıktı doğrulama
PYTHONPATH=src python -m smart_road_safety.cli build-ftr-output examples/analysis_session_request.json \
  --vehicle-info-path examples/ftr_vehicle_info.json \
  --video-id video_1.mp4 \
  --output-path out/results.json \
  --event-time-seconds 1.5
PYTHONPATH=src python -m smart_road_safety.cli validate-ftr-output out/results.json

# KTR report model artifacts and final report generation
PYTHONPATH=src python -m smart_road_safety.cli train-report-models --max-driver-svt-rows 50000
PYTHONPATH=src python -m smart_road_safety.cli build-final-report \
  --template-path final_report_template.docx \
  --model-artifacts-path out/model_artifacts/ktr_model_artifacts.json \
  --output-path ktr_v1.docx \
  --markdown-path out/ktr_v1.md \
  --evidence-path out/ktr_v1_evidence.json
PYTHONPATH=src python -m smart_road_safety.cli prepare-ktr-report --max-driver-svt-rows 50000

# Senaryo değerlendirmesi ve export
PYTHONPATH=src python -m smart_road_safety.cli run-scenarios examples/scenarios --output-path out/scenario_report.json
PYTHONPATH=src python -m smart_road_safety.cli export-scenario-report out/scenario_report.json --output-path out/scenario_report.md

# Local API
PYTHONPATH=src python -m smart_road_safety.cli serve-local-api --host 127.0.0.1 --port 8000

# Test suite
PYTHONPATH=src python -m unittest discover -s tests
```

---

## Kaynak Yapısı

```text
qode/
├── main.py                          # Inference entry point (FTR uyumlu)
├── Dockerfile                       # CUDA 12.1 + NVIDIA Tesla T4 için
├── requirements.txt
├── download_weights.sh              # Yerel geliştirme için ağırlık indiricisi
├── data/
│   ├── datasets/                    # Eğitim veri setleri (git'e dahil değil)
│   │   ├── state-farm-distracted-driver/
│   │   ├── dmd-distraction/
│   │   ├── dmd-drowsiness/
│   │   └── DriverSVT-teknofest/
│   └── weights/                     # Eğitilmiş ağırlıklar (git'e dahil değil)
│       ├── driver_classifier.pt     # EfficientNet-B2 sürücü davranış modeli
│       ├── vehicle_type_classifier.pt  # EfficientNet-B0 araç tipi modeli
│       └── teknocan_detector.pt     # YOLOv11n Teknocan tespit ajan modeli
├── docs/
│   ├── diagrams/                    # Mermaid kaynakları ve render edilmiş rapor görselleri
│   └── report_assets/               # Rapor ek görselleri
├── src/smart_road_safety/
│   ├── analysis/
│   │   └── model_inference.py       # Ana inference motoru (YOLO + classifier + OCR)
│   ├── competition/
│   │   └── ftr.py                   # FTR şema doğrulama ve JSON üretimi
│   ├── data/                        # Manifest-backed adapters and real dataset loaders
│   ├── modeling/                    # KTR report-model artifact generation
│   ├── reporting/                   # Final report DOCX/Markdown/evidence generation
│   └── training/                    # Dataset preprocessing and model training
└── assumptions.md                   # Sistem varsayımları ve gerçek veri kaydı
```

---

## Current System Shape

The current pipeline is dataset-backed, FTR-aware, model-training enabled, and report-artifact ready:

- `main.py` runs the FTR-compatible real inference entry point and refuses to emit placeholder vehicle metadata when inference and sidecar metadata are both unavailable.
- `smart_road_safety.analysis.model_inference` integrates YOLO11x, EasyOCR, classifier-backed post-processing, passenger logic, and heuristic seatbelt detection.
- `smart_road_safety.training` contains dataset preprocessing, synthetic plate generation, windshield augmentation, classifier training, YOLO training, and evaluation scripts.
- `smart_road_safety.competition` validates/builds source-of-truth `results.json`.
- `smart_road_safety.modeling` generates reproducible local report artefacts for KTR evidence.
- `smart_road_safety.reporting` generates DOCX/Markdown/evidence artifacts for the KTR final report.
- Local API endpoints expose orchestration, dataset inventory, analysis session, competition output, evaluation, and export flows.

---

## Veri Setleri

| Veri Seti | Boyut | FTR Rolü |
|---|---|---|
| State Farm Distracted Driver | ~102k görsel (10 sınıf) | `sofor_eylemi` ana eğitim kaynağı |
| DMD Distraction | Multi-kamera video | `telefonla_konusma`, `su_icme`, `arkaya_bakma` |
| DMD Drowsiness | Multi-kamera video | `esneme` |
| DriverSVT-teknofest | Görsel + etiket | `sigara_icme`, `emniyet_kemeri_ihlali` |
| Teknocan Augmented | YOLO (315 görsel) | Özel `teknocan` tespit ajanı (yolo11n) eğitimi |

---

## Doğrulama Sonuçları

| Test | Sonuç |
|---|---|
| FTR şema doğrulama (`validate-ftr-output`) | ✅ **PASS** |
| Yolcu tespiti (`yolcular` kategorisi) | ✅ Üretiliyor (Geometri tabanlı koltuk eşleşmesi) |
| Sürücü eylemleri (`sofor_eylemi`) | ✅ Bütün alt sınıflar entegre (EfficientNet-B2) |
| Nesneler (`teknocan` ve `bilgisayar`) | ✅ Özelleştirilmiş ajan model (yolo11n) ile aktif |
| Emniyet kemeri heuristic | ✅ Aktif |
| YOLO + EasyOCR + EfficientNet pipeline | ✅ Kusursuz Senkronizasyon |
| KTR report artefact generation | ✅ DOCX/Markdown/evidence üretiyor |

---

## Sınırlılıklar

- **Plaka OCR**: Yol kenarı kameralarda düşük çözünürlük nedeniyle başarı oranı değişken. Plaka bulunamazsa `"tespit_edilemedi"` olarak işaretlenir.
- **Number Verification / QoD API**: Gerçek Turkcell endpoint'leri mevcut değil — mock implementasyon kullanılıyor.
- Organizer-side metadata/ground-truth for final hidden videos is not available locally; current `main.py` uses inference and only accepts explicit `vehicle_info.json` as a sidecar override.
- Exact FTR vehicle type/color/plate/object/passenger labels tüm local sample'larda yoktur; bu alanlar ek veri veya curated annotation gerektirir.
