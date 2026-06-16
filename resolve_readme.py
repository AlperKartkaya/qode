import re

with open("README.md", "r") as f:
    content = f.read()

# 1. Kaynak Yapısı
c1_head = """<<<<<<< HEAD
├── docs/
│   ├── diagrams/                    # Mermaid kaynakları ve render edilmiş rapor görselleri
│   └── report_assets/               # Rapor ek görselleri
=======
│       ├── driver_classifier.pt     # EfficientNet-B2 sürücü davranış modeli
│       ├── vehicle_type_classifier.pt  # EfficientNet-B0 araç tipi modeli
│       └── teknocan_detector.pt     # YOLOv11n Teknocan tespit ajan modeli
>>>>>>> feat/ai-model"""

c1_resolved = """│       ├── driver_classifier.pt     # EfficientNet-B2 sürücü davranış modeli
│       ├── vehicle_type_classifier.pt  # EfficientNet-B0 araç tipi modeli
│       └── teknocan_detector.pt     # YOLOv11n Teknocan tespit ajan modeli
├── docs/
│   ├── diagrams/                    # Mermaid kaynakları ve render edilmiş rapor görselleri
│   └── report_assets/               # Rapor ek görselleri"""

content = content.replace(c1_head, c1_resolved)

# 2. Current System Shape
c2_head = """<<<<<<< HEAD
The current pipeline is dataset-backed, FTR-aware, model-training enabled, and report-artifact ready:

- `main.py` runs the FTR-compatible real inference entry point and refuses to emit placeholder vehicle metadata when inference and sidecar metadata are both unavailable.
- `smart_road_safety.analysis.model_inference` integrates YOLO11x, EasyOCR, classifier-backed post-processing, passenger logic, and heuristic seatbelt detection.
- `smart_road_safety.training` contains dataset preprocessing, synthetic plate generation, windshield augmentation, classifier training, YOLO training, and evaluation scripts.
- `smart_road_safety.competition` validates/builds source-of-truth `results.json`.
- `smart_road_safety.modeling` generates reproducible local report artefacts for KTR evidence.
- `smart_road_safety.reporting` generates DOCX/Markdown/evidence artifacts for the KTR final report.
- Local API endpoints expose orchestration, dataset inventory, analysis session, competition output, evaluation, and export flows.
=======
| Veri Seti | Boyut | FTR Rolü |
|---|---|---|
| State Farm Distracted Driver | ~102k görsel (10 sınıf) | `sofor_eylemi` ana eğitim kaynağı |
| DMD Distraction | Multi-kamera video | `telefonla_konusma`, `su_icme`, `arkaya_bakma` |
| DMD Drowsiness | Multi-kamera video | `esneme` |
| DriverSVT-teknofest | Görsel + etiket | `sigara_icme`, `emniyet_kemeri_ihlali` |
| Teknocan Augmented | YOLO (315 görsel) | Özel `teknocan` tespit ajanı (yolo11n) eğitimi |
>>>>>>> feat/ai-model"""

c2_resolved = """The current pipeline is dataset-backed, FTR-aware, model-training enabled, and report-artifact ready:

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
| Teknocan Augmented | YOLO (315 görsel) | Özel `teknocan` tespit ajanı (yolo11n) eğitimi |"""

content = content.replace(c2_head, c2_resolved)

# 3. Doğrulama Sonuçları
c3_head = """<<<<<<< HEAD
| FTR şema doğrulama (`validate-ftr-output`) | ✅ PASS |
| Yolcu tespiti (`yolcular` kategorisi) | ✅ Üretiliyor |
| Sürücü eylemleri (`sofor_eylemi`) | ✅ 4+ sınıf aktif / genişletiliyor |
| Emniyet kemeri heuristic | ✅ Aktif |
| YOLO + EasyOCR + EfficientNet pipeline | ✅ Çalışıyor |
| KTR report artefact generation | ✅ DOCX/Markdown/evidence üretiyor |
=======
| FTR şema doğrulama (`validate-ftr-output`) | ✅ **PASS** |
| Yolcu tespiti (`yolcular` kategorisi) | ✅ Üretiliyor (Geometri tabanlı koltuk eşleşmesi) |
| Sürücü eylemleri (`sofor_eylemi`) | ✅ Bütün alt sınıflar entegre (EfficientNet-B2) |
| Nesneler (`teknocan` ve `bilgisayar`) | ✅ Özelleştirilmiş ajan model (yolo11n) ile aktif |
| Emniyet kemeri heuristic | ✅ Aktif |
| YOLO + EasyOCR + EfficientNet pipeline | ✅ Kusursuz Senkronizasyon |
>>>>>>> feat/ai-model"""

c3_resolved = """| FTR şema doğrulama (`validate-ftr-output`) | ✅ **PASS** |
| Yolcu tespiti (`yolcular` kategorisi) | ✅ Üretiliyor (Geometri tabanlı koltuk eşleşmesi) |
| Sürücü eylemleri (`sofor_eylemi`) | ✅ Bütün alt sınıflar entegre (EfficientNet-B2) |
| Nesneler (`teknocan` ve `bilgisayar`) | ✅ Özelleştirilmiş ajan model (yolo11n) ile aktif |
| Emniyet kemeri heuristic | ✅ Aktif |
| YOLO + EasyOCR + EfficientNet pipeline | ✅ Kusursuz Senkronizasyon |
| KTR report artefact generation | ✅ DOCX/Markdown/evidence üretiyor |"""

content = content.replace(c3_head, c3_resolved)

# 4. Sınırlılıklar
c4_head = """<<<<<<< HEAD
- Plaka OCR: yol kenarı kameralarda düşük çözünürlük nedeniyle başarı oranı değişken; plaka bulunamazsa `tespit_edilemedi` olarak işaretlenir.
- Araç tipi sınıflandırıcısı: eğitim verisi ve model ağırlığı durumuna göre EfficientNet-B0 ya da YOLO COCO sınıf eşlemesi kullanılır.
- `sigara_icme` / `esneme` / `slalom`: State Farm tek başına bu sınıfları kapsamaz; DMD, DriverSVT, synthetic/curated data ve temporal logic ile tamamlanır.
- Exact FTR vehicle type/color/plate/object/passenger labels tüm local sample'larda yoktur; bu alanlar ek veri veya curated annotation gerektirir.
- Organizer-side metadata/ground-truth for final hidden videos is not available locally; current `main.py` uses inference and only accepts explicit `vehicle_info.json` as a sidecar override.
- Real Number Verification ve QoD endpoint'leri mevcut değildir; bu destek/demo servisleri KTR final rapor kapsamı dışında tutulur.
=======
- **Plaka OCR**: Yol kenarı kameralarda düşük çözünürlük nedeniyle başarı oranı değişken. Plaka bulunamazsa `"tespit_edilemedi"` olarak işaretlenir.
- **Number Verification / QoD API**: Gerçek Turkcell endpoint'leri mevcut değil — mock implementasyon kullanılıyor.
>>>>>>> feat/ai-model"""

c4_resolved = """- **Plaka OCR**: Yol kenarı kameralarda düşük çözünürlük nedeniyle başarı oranı değişken. Plaka bulunamazsa `"tespit_edilemedi"` olarak işaretlenir.
- **Number Verification / QoD API**: Gerçek Turkcell endpoint'leri mevcut değil — mock implementasyon kullanılıyor.
- Organizer-side metadata/ground-truth for final hidden videos is not available locally; current `main.py` uses inference and only accepts explicit `vehicle_info.json` as a sidecar override.
- Exact FTR vehicle type/color/plate/object/passenger labels tüm local sample'larda yoktur; bu alanlar ek veri veya curated annotation gerektirir."""

content = content.replace(c4_head, c4_resolved)

with open("README.md", "w") as f:
    f.write(content)
