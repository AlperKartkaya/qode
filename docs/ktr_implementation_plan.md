# KTR / FTR Report And Model Implementation Plan

Current source of truth for this milestone:

1. `5G_ve_Yapay_Zeka_ile_Akıllı_Yol_Güvenliği_Yarışması_-_FTR_Aşaması_Teslim_D.pdf` — exact FTR output schema, allowed labels, Docker/input-output contract, runtime constraints.
2. `final_report_template.docx` — final report sections, scoring weights, formatting constraints, 3–15 page boundary.
3. Repo evidence — manifests, adapters, FTR validator, trained local model artifacts, generated report files.

The 2026 şartname remains background context, but telecom/API quality escalation is explicitly out of the KTR final-report scope for this implementation pass. The report must focus on the AI/video pipeline, datasets, trained model evidence, FTR schema compliance, and source-code traceability.

## 1. FTR Requirements Extracted

The final inference output must be written to `/app/data/output/results.json` and must use this shape:

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
    }
  ]
}
```

Valid labels:

| Field | Allowed values |
| --- | --- |
| `arac_bilgisi.tip` | `sedan`, `suv`, `hatchback`, `pickup`, `minibus`, `panelvan`, `kamyon` |
| `arac_bilgisi.renk` | `beyaz`, `siyah`, `gri`, `kirmizi`, `mavi`, `sari`, `yesil`, `turuncu`, `kahverengi` |
| `tespitler.kategori` | `sofor_eylemi`, `nesneler`, `yolcular` |
| `sofor_eylemi` labels | `arkaya_bakma`, `esneme`, `sigara_icme`, `su_icme`, `telefonla_konusma`, `slalom`, `etrafa_bakinma`, `emniyet_kemeri_ihlali` |
| `nesneler` labels | `teknocan`, `bilgisayar` |
| `yolcular` labels | `arka_koltuk_1`, `arka_koltuk_2`, `on_koltuk` |

Hard rules:

- JSON keys and label values must match exactly.
- Labels must be ASCII-safe; no Turkish characters in emitted labels.
- Plate text must match the Turkish plate regex after normalization.
- Each detection needs its own timestamp and confidence score.
- Runtime must read `/app/data/input/video.mp4`, write `/app/data/output/results.json`, and fit the FTR Docker/T4 resource budget.

## 2. Report Template Requirements

`final_report_template.docx` requires these sections:

1. **PROJE ÖZETİ (5 puan)** — concise project summary.
2. **VERİSETİ OLUŞTURULMASI (20 puan)** — data sources, labeling, balancing, augmentation, train/validation/test split rationale.
3. **YAPAY ZEKÂ ÇÖZÜMÜ (50 puan)** — problem analysis, architecture, technical details.
4. **ÇÖZÜMÜN SINANMASI (20 puan)** — evidence-backed metrics such as accuracy, precision, recall, F1, FPS.
5. **KAYNAKÇA (5 puan)** — technical and dataset references.

The generator now produces both:

- `ktr_v1.docx` — DOCX following the template section order, strict final_report_template.docx style rules, rendered Mermaid diagrams, and image-based code appendices.
- `out/ktr_v1.md` — text QA artifact for review/diff.
- `out/ktr_v1_evidence.json` — structured evidence backing the report.

## 3. Current Repo Compliance Audit

| Area | Current state | FTR/KTR fit | Required action/status |
| --- | --- | --- | --- |
| FTR contract | `src/smart_road_safety/competition/ftr.py` validates exact keys, labels, plate regex, confidence, timestamps | Aligned | Keep as source-of-truth output bridge. |
| Dataset adapters | State Farm, DMD distraction, DMD drowsiness, DriverSVT, legacy 3-video bundle | Useful support data, incomplete FTR coverage | Keep manifests gap-aware; do not claim full coverage. |
| Model artifacts | `src/smart_road_safety/modeling/report_models.py` trains reproducible local baselines | Gives report-ready evidence now | Add deep model weights later under same artifact pattern. |
| Report generator | `src/smart_road_safety/reporting/final_report.py` builds DOCX/Markdown/evidence | Aligned with template | Use `prepare-ktr-report` for one-command generation. |
| FTR CLI | `build-ftr-output`, `validate-ftr-output` | Aligned | Use for schema smoke and final wrapper validation. |
| Docker submission | `main.py` and `Dockerfile` present after teammate merge; wrapper uses explicit sidecars or curated local samples and fails loudly when arbitrary-video inference weights are unavailable | Partially aligned | Add final deep model weights/inference before hidden-video submission. |

## 4. Dataset Strategy

No single public or local dataset covers all FTR labels. The report should show a multi-source strategy and state the gaps honestly.

| Dataset | Coverage | Caveat | Use |
| --- | --- | --- | --- |
| Current legacy 3 videos | TOGG-like approach, plate visibility, smoking, phone, slalom-like behavior | No exact plate text/type/color/passengers/object labels | FTR-output smoke tests and curated annotation seed. |
| State Farm Distracted Driver | phone/texting, drinking, reaching, passenger talking | Image-only; no vehicle/plate | Driver-action pretraining and subject-grouped validation. |
| DMD Distraction | phonecall, texting, drinking, gaze, reaching, hand-wheel states | Partial FTR mapping | Main cabin action/gaze temporal data source. |
| DMD Drowsiness | yawning, eye state, blinking | No vehicle/plate/object/passenger | `esneme`/fatigue support. |
| DriverSVT | telemetry speed, dangerous state, phone/smoking/seatbelt/drowsiness labels | Telemetry, not visual output | Speed/slalom/risk ablation and fusion narrative. |
| CompCars | vehicle type/fine-grained make/model | License/access review needed | Vehicle type classifier pretraining. |
| UFPR-VCR | vehicle color + coarse vehicle categories | Academic-use terms | Vehicle color recognition benchmark. |
| CCPD | plate detection/OCR pretraining | Chinese plate format; locale mismatch | Plate localization/OCR pretraining only. |
| BrnoCompSpeed / VS13 | speed estimation benchmarks | Calibration-heavy / smaller scope | Speed method validation. |
| Drive&Act / TICaM | in-cabin activities, occupants, objects | Access/license review needed | Passenger/object action support. |

Source links for acquisition/license review:

- CompCars: <https://mmlab.ie.cuhk.edu.hk/datasets/comp_cars/>
- UFPR-VCR: <https://github.com/lima001/ufpr-vcr-dataset>
- CCPD: <https://github.com/detectrecog/ccpd>
- BrnoCompSpeed: <https://github.com/JakubSochor/BrnoCompSpeed>
- VS13: <https://slobodan.ucg.ac.me/science/vs13/>
- DMD: <https://dmd.vicomtech.org/>
- Drive&Act: <https://driveandact.com/>
- TICaM: <https://vizta-tof.kl.dfki.de/cabin-dataset/>

## 5. Model Selection

| Task | Primary model | Reason |
| --- | --- | --- |
| Vehicle / plate / object detection | YOLO11n/s | T4-friendly real-time baseline and simple export path. |
| Detection ablation | RT-DETR | Accuracy comparison when YOLO misses small/occluded targets. |
| Plate OCR | YOLO plate crop + PaddleOCR | OCR result can be normalized and regex-validated before FTR output. |
| Driver actions | VideoMAE / SlowFast via MMAction2 | Temporal cues improve yawning, looking away, phone, smoking, drinking detection. |
| Tracking / speed / slalom | ByteTrack + homography/calibration | Track-level motion is necessary for speed/slalom, not just frame labels. |

References:

- YOLO11: <https://docs.ultralytics.com/models/yolo11/>
- RT-DETR: <https://docs.ultralytics.com/models/rtdetr/>
- PaddleOCR: <https://paddlepaddle.github.io/PaddleOCR/main/en/index.html>
- MMAction2: <https://mmaction2.readthedocs.io/en/latest/model_zoo/recognition.html>
- ByteTrack: <https://github.com/FoundationVision/ByteTrack>

## 6. Implemented Command Flow

```bash
PYTHONPATH=src python3 -m smart_road_safety.cli train-report-models \
  --max-driver-svt-rows 50000

PYTHONPATH=src python3 -m smart_road_safety.cli build-final-report \
  --template-path final_report_template.docx \
  --model-artifacts-path out/model_artifacts/ktr_model_artifacts.json \
  --output-path ktr_v1.docx \
  --markdown-path out/ktr_v1.md \
  --evidence-path out/ktr_v1_evidence.json

PYTHONPATH=src python3 -m smart_road_safety.cli prepare-ktr-report \
  --max-driver-svt-rows 50000
```

Current trained report artifacts:

- `state_farm_driver_action_prior.json`
- `dmd_distraction_action_prior.json`
- `dmd_drowsiness_action_prior.json`
- `driver_svt_telemetry_centroid.json`
- bundle: `ktr_model_artifacts.json`

These are lightweight, reproducible baselines. They ground the report today and define the artifact shape that later deep-learning weights and metrics should fill. `docs/diagrams/*.mmd`, `docs/diagrams/rendered/*.png`, and `docs/report_assets/code_snippets/*.png` add rendered architecture and source-code traceability to the KTR v1 report without displaying raw code blocks.

## 7. KTR Report Filling Plan

### 1. PROJE ÖZETİ

Explain the end-to-end video analysis system: video input, vehicle/plate/risk extraction, FTR `results.json`, source-code traceability, and report artifact generation.

### 2. VERİSETİ OLUŞTURULMASI

Include dataset table, FTR coverage families, known gaps, split strategy, balancing rationale, augmentation plan, and source references.

### 3.1. PROBLEMİN ANALİZİ

Discuss lighting, blur, occlusion, plate smallness, cabin reflections, temporal behavior windows, and sparse object/passenger labels.

### 3.2. ÇÖZÜM MİMARİSİ

Show components:

1. video input,
2. manifest/data adapter layer,
3. model inference layer,
4. FTR label mapping and validation,
5. `results.json` writer,
6. report/evidence generator.

### 3.3. ÇÖZÜM DETAYLARI

Describe YOLO11/RT-DETR, PaddleOCR, VideoMAE/SlowFast, ByteTrack/homography, confidence thresholding, FTR label validation, and runtime packaging.

### 4. ÇÖZÜMÜN SINANMASI

Include current baseline metrics, then reserve table rows for final mAP/OCR/F1/FPS measurements once deep weights are added.

| Task | Metrics |
| --- | --- |
| Vehicle type/color | accuracy, macro-F1 |
| Plate detection | mAP, precision, recall |
| Plate OCR | exact-match rate, regex-valid rate |
| Driver actions | per-label precision, recall, F1, temporal IoU |
| Objects/passengers | mAP/F1 |
| Speed | MAE/RMSE if labelled |
| Runtime | FPS, p50/p95 latency, Docker runtime |

### 5. KAYNAKÇA

Use FTR document, report template, dataset pages, model framework docs, and repo paths.

## 8. Remaining Work Before Final Submission

- Add FTR-aligned labels for exact plate text, vehicle type/color, passengers, `teknocan`, and `bilgisayar`.
- Train and export deep model weights for the selected architectures.
- Replace the current explicit-sidecar/curated-sample Docker wrapper with trained arbitrary-video inference once final weights are available.
- Measure FPS/latency and final per-label metrics.
- Replace report placeholders for team/app IDs with official values.
