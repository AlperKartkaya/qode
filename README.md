# QoDe — Smart Road Safety (5G & AI)

**TEKNOFEST 2026 — 5G ve Yapay Zekâ ile Akıllı Yol Güvenliği Yarışması — FTR Aşaması**

## Proje Özeti

QoDe, yol kenarı kameralarından gelen video akışını gerçek zamanlı analiz eden bir yapay zekâ sistemidir. Araç tipini, rengini, plakasını ve kabin içi davranışları (sürücü eylemleri, yolcular, nesneler) tespit ederek FTR şartnamesine uygun `results.json` üretir.

---

## Mimari

```
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

# 3. Araç tipi sınıflandırıcısını eğit (veri hazır olunca, bkz. train_vehicle_type_classifier.py)
python -m smart_road_safety.training.train_vehicle_type_classifier

# 4. Sınıflandırıcı değerlendirmesi
PYTHONPATH=src python -m smart_road_safety.training.eval_classifier
```

---

## Docker ile Çalıştırma

**Önemli:** `docker build` öncesinde `data/weights/driver_classifier.pt` dosyasının mevcut olması gerekir. Bunu yukarıdaki eğitim adımlarıyla oluşturun.

```bash
# 1. Image oluştur (model ağırlıkları bu aşamada indirilir — timeout'a dahil değil)
docker build -t teknofest/qode:latest .

# 2. Değerlendirme ortamına uygun şekilde çalıştır
docker run --rm --gpus all \
  -v /path/to/video.mp4:/app/data/input/video.mp4 \
  -v /path/to/output:/app/data/output \
  teknofest/qode:latest

# Sonuç: /path/to/output/results.json
```

---

## Yerel Test

```bash
# Test klibi ile pipeline'ı çalıştır
python main.py

# FTR şema doğrulama
PYTHONPATH=src python -m smart_road_safety.cli validate-ftr-output out/results.json
```

---

## CLI Komutları

```bash
# Assumptions ve manifest kontrolü
PYTHONPATH=src python -m smart_road_safety.cli print-assumptions
PYTHONPATH=src python -m smart_road_safety.cli check-manifest data/datasets/state-farm-distracted-driver/manifest.json

# Dataset incelemesi
PYTHONPATH=src python -m smart_road_safety.cli inspect-dataset data/datasets/state-farm-distracted-driver/manifest.json \
  --dataset-root data/datasets/state-farm-distracted-driver

# FTR çıktı doğrulama
PYTHONPATH=src python -m smart_road_safety.cli validate-ftr-output out/results.json

# Senaryo değerlendirmesi
PYTHONPATH=src python -m smart_road_safety.cli run-scenarios examples/scenarios \
  --output-path out/scenario_report.json

# Test suite
PYTHONPATH=src python -m unittest discover -s tests
```

---

## Kaynak Yapısı

```
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
├── src/smart_road_safety/
│   ├── analysis/
│   │   └── model_inference.py       # Ana inference motoru (YOLO + classifier + OCR)
│   ├── competition/
│   │   └── ftr.py                   # FTR şema doğrulama ve JSON üretimi
│   └── training/
│       ├── train_classifier.py      # EfficientNet-B2 sürücü eğitimi
│       ├── train_vehicle_type_classifier.py  # EfficientNet-B0 araç tipi eğitimi
│       ├── preprocess_state_farm.py # State Farm veri ön işleme
│       └── windshield_simulator.py  # Cam yansıma augmentasyonu
└── assumptions.md                   # Sistem varsayımları ve gerçek veri kaydı
```

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

---

## Sınırlılıklar

- **Plaka OCR**: Yol kenarı kameralarda düşük çözünürlük nedeniyle başarı oranı değişken. Plaka bulunamazsa `"tespit_edilemedi"` olarak işaretlenir.
- **Number Verification / QoD API**: Gerçek Turkcell endpoint'leri mevcut değil — mock implementasyon kullanılıyor.
