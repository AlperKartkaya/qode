# KTR / FTR Implementation Plan

Source of truth:

- `5G_ve_Yapay_Zeka_ile_Akıllı_Yol_Güvenliği_Yarışması_-_FTR_Aşaması_Teslim_D.pdf`
- `2026_5G_YAPAY_ZEKA_İLE_AKILLI_YOL_GÜVENLİĞİ_YARISMASI_SARTNAMESI_2_PORZ6.pdf`
- `final_report_template.docx`

This document is the working plan for turning the current dataset-backed scaffold into the KTR/FTR submission path.

## 1. Source-Of-Truth Requirements Extracted

### 1.1 FTR output contract

The final inference output must be written to `/app/data/output/results.json` and must use this consolidated shape:

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
- Labels must be ASCII-safe; no Turkish characters.
- Plate text must match the Turkish plate regex from the FTR document after normalization.
- Each detection needs its own timestamp and confidence score.
- The Dockerized program must read `/app/data/input/video.mp4`, write `/app/data/output/results.json`, start automatically, and finish within the 10-minute Tesla T4 budget.

### 1.2 Şartname scoring priorities

The 2026 şartname makes these axes central:

1. AI analysis accuracy and precision for vehicle, plate, real speed, in-cabin object, and risk detection.
2. 5G API integration, especially selective QoD usage only when quality is needed.
3. Final report and presentation quality, including modern software architecture and development method.

The report and implementation should therefore avoid a driver-behavior-only story. It must explicitly cover TOGG/vehicle approach, plate, vehicle metadata, in-cabin/risk labels, speed strategy, and QoD selectivity.

## 2. Current Repo Compliance Audit

| Area | Current state | FTR/KTR fit | Required action |
| --- | --- | --- | --- |
| Dataset adapters | State Farm, DMD distraction, DMD drowsiness, DriverSVT, legacy 3-video bundle | Good support-data foundation, but incomplete FTR coverage | Keep adapters; mark them as support datasets and add gap-aware manifest metadata. |
| Analysis contract | `AnalysisResult` supports vehicle boolean, plate visibility, driver risk label | Useful for orchestration, insufficient for `results.json` | Add separate FTR competition output contract and converter. Done in `src/smart_road_safety/competition/`. |
| Manifests | Previously treated driver behavior as enough | Now contradicted by FTR target taxonomy | Manifest checker now reports FTR family/plate gaps instead of silently passing support datasets. |
| Orchestration/QoD | QoD trigger uses TOGG confidence, plate visibility, driver risk | Directionally aligned with şartname | Keep configurable policy; calibrate after real videos/API details. |
| Number Verification/QoD clients | Interfaces + mocks only | Correct until credentials arrive | Keep mock boundaries explicit; implement real clients only after Turkcell base URL/auth/profile details arrive. |
| Local API/CLI | Dataset inventory, analysis session, scenarios, markdown export | Missing FTR output surface | Add FTR output generation/validation endpoints and CLI commands. Done. |
| Evaluation | Scenario scoring over internal orchestration labels | Good for architecture proof, not FTR evaluator | Add exact `results.json` validation and later mAP/F1/FPS metric scripts. |
| Docker submission | Not yet present | Required | Add root `Dockerfile`, `requirements.txt`, `main.py`, `/app/models/` packaging before final delivery. |

## 3. Dataset Strategy

No single public dataset covers all FTR labels. Use a multi-source strategy and document gaps honestly.

| Dataset | Coverage | Caveat | Use |
| --- | --- | --- | --- |
| Current legacy 3 videos | TOGG-like approach, plate visibility, smoking, phone, slalom-like behavior | No exact plate text/type/color/passengers/object labels | Local FTR-output smoke tests and demo cases. |
| State Farm Distracted Driver | phone/texting, drinking, reaching, passenger talking | Not vehicle/plate; image not video | Driver action pretraining and subject-grouped validation. |
| DMD Distraction | phonecall, texting, drinking, gaze, reaching, hand-wheel states | Gated academic dataset; partial FTR mapping | Main driver-action and gaze/action source. |
| DMD Drowsiness | yawning, eye state, blinking | No vehicle/plate/object/passenger | `esneme` and fatigue support. |
| DriverSVT | telemetry speed, dangerous state, phone/smoking/seatbelt/drowsiness labels | Telemetry, not visual output | Speed/slalom/risk ablation and sensor-fusion narrative. |
| CompCars | vehicle type/fine-grained make/model | Academic page; license must be checked before redistribution | Vehicle type classifier pretraining. |
| UFPR-VCR | vehicle color + coarse vehicle categories | Academic/research access agreement | Vehicle color recognition benchmark. |
| CCPD | plate detection/OCR pretraining | Chinese plate format; MIT, but locale mismatch | Plate localization/OCR pretraining only. |
| BrnoCompSpeed | calibrated traffic video speed estimation | Large/calibration-heavy | Speed estimation benchmark and method reference. |
| VS13 | single-vehicle pass-by speed data | Smaller and not dense traffic | Lightweight speed sanity benchmark. |
| Drive&Act | fine-grained in-cabin activities | Research-use terms | Additional temporal action recognition. |
| TICaM | in-cabin occupants/objects, 2D/3D labels | Account/gated; license check needed | Passenger/object detection. |
| Smoker Detection Dataset | smoking class | Not vehicle-specific | Auxiliary smoking classifier pretraining. |

Source links for acquisition/license review:

- CompCars: <https://mmlab.ie.cuhk.edu.hk/datasets/comp_cars/>
- UFPR-VCR: <https://github.com/lima001/ufpr-vcr-dataset>
- CCPD: <https://github.com/detectrecog/ccpd>
- BrnoCompSpeed: <https://github.com/JakubSochor/BrnoCompSpeed>
- VS13: <https://slobodan.ucg.ac.me/science/vs13/>
- DMD: <https://dmd.vicomtech.org/>
- Drive&Act: <https://driveandact.com/>
- TICaM: <https://vizta-tof.kl.dfki.de/cabin-dataset/>
- Smoker Detection Dataset: <https://data.mendeley.com/datasets/j45dj8bgfc/1>

### Immediate data-gap actions

1. Curate FTR-aligned labels for the 3 local videos:
   - vehicle type, color, exact plate if readable, timestamped detections.
2. Add at least one small custom annotation file for:
   - `teknocan`, `bilgisayar`, `yolcular` positions if these objects appear in any available/recorded material.
3. Add a synthetic Turkish plate augmentation pipeline only for OCR robustness, clearly separated from real validation metrics.
4. Treat `slalom` as a trajectory/motion classification problem, not a cabin action class.
5. Treat `emniyet_kemeri_ihlali` as a custom-label gap unless a verified dataset is acquired.

## 4. Model Selection

### 4.1 Detection and tracking

Primary recommendation: **YOLO11 small/medium**.

- Use for vehicle detection, plate localization, cabin object/person detection.
- Advantages: strong real-time deployment story, simple ONNX/TensorRT path, clear T4 runtime fit.
- Risk: must be fine-tuned for cabin/plate domains.

Alternative: **RT-DETR**.

- Use if YOLO accuracy on vehicle/plate/cabin object detection is insufficient.
- Keep as an ablation, not the first implementation path.

Tracking: **ByteTrack** over vehicle boxes.

- Use for stable vehicle track IDs and speed/approach features.
- Pair with camera calibration or homography for speed estimation.

References:

- YOLO11: <https://docs.ultralytics.com/models/yolo11/>
- RT-DETR: <https://docs.ultralytics.com/models/rtdetr/>
- ByteTrack: <https://github.com/FoundationVision/ByteTrack>

### 4.2 Plate OCR

Primary recommendation: **YOLO plate detector + PaddleOCR PP-OCRv3/PP-OCRv4 fine-tuned on plate crops**.

Post-processing:

- uppercase alphanumeric normalization,
- Turkish plate regex validation,
- confidence thresholding,
- return only regex-conforming strings to FTR output.

Reference: <https://paddlepaddle.github.io/PaddleOCR/main/en/index.html>

### 4.3 Driver actions

Primary recommendation: staged model:

1. fast frame-level detector/classifier for obvious cues (`telefonla_konusma`, `sigara_icme`, `su_icme`),
2. temporal action model for ambiguous events (`esneme`, `arkaya_bakma`, `etrafa_bakinma`),
3. motion/trajectory logic for `slalom`.

Candidate model families:

- **VideoMAE / MViT / SlowFast via MMAction2** for clip-level temporal action recognition.
- Lightweight CNN/ViT image classifier for State Farm-like still-frame cues.
- MediaPipe/landmark features only as auxiliary fatigue/yawn signals, not the primary final proof.

Reference: <https://mmaction2.readthedocs.io/en/latest/model_zoo/recognition.html>

### 4.4 Speed estimation

Preferred final approach:

1. detect vehicle,
2. track with ByteTrack,
3. estimate image-plane displacement,
4. transform using calibrated camera geometry/homography,
5. smooth over a track window,
6. keep the output internal unless FTR schema adds a speed key.

KTR report should explain that speed is required by şartname but absent from the current FTR JSON schema, so it will be evaluated internally and surfaced in UI/report if the schema is updated.

### 4.5 QoD policy model

Use deterministic policy first, then calibrate:

- trigger if target vehicle/TOGG confidence is high and distance/scale indicates approach,
- trigger if plate is visible but OCR confidence is below final threshold,
- trigger if high-risk driver/in-cabin event is detected,
- avoid repeated QoD requests while already boosted.

Keep this policy explainable; it is directly reportable and easier to defend than a black-box network policy.

## 5. Implementation Work Plan

### Phase 1 — Contract hardening (done / in progress)

- Update `assumptions.md` to FTR/şartname reality.
- Add `smart_road_safety.competition` FTR schema dataclasses and validation.
- Add CLI:
  - `build-ftr-output`
  - `validate-ftr-output`
- Add Local API endpoints:
  - `/competition/ftr-output`
  - `/competition/validate-ftr-output`
- Update manifest metadata and checker to expose FTR gaps.
- Add unit tests for FTR schema and API.

### Phase 2 — Data curation

- Add `data/ftr_annotations/` with a small source-controlled annotation schema for local/curated labels.
- Convert legacy observations into timestamped FTR events where evidence exists.
- Add plate/type/color fields only when visually verified; do not invent missing labels.
- Create train/val/test split manifests:
  - State Farm: subject-grouped.
  - DMD: subject/session-grouped.
  - DriverSVT: user-grouped.
  - FTR local holdout: video-grouped.

### Phase 3 — Baseline models

- Vehicle/plate detector baseline: YOLO11n/s.
- Plate OCR baseline: PaddleOCR fine-tuned or evaluated on normalized plate crops.
- Driver action baseline:
  - image classifier for State Farm-compatible classes,
  - DMD action parser + temporal model for video classes,
  - custom mapping to FTR labels.
- Speed baseline: ByteTrack + homography placeholder calibrated on available video geometry.

### Phase 4 — Runtime packaging

- Add root `main.py` that reads `/app/data/input/video.mp4` and writes `/app/data/output/results.json`.
- Add root `Dockerfile` using `nvidia/cuda:12.1.0-base-ubuntu22.04`.
- Add `requirements.txt` with pinned runtime dependencies.
- Keep image size under 8 GB; move large training-only dependencies out of runtime.
- Add `models/README.md` explaining expected weight filenames without committing large weights unless explicitly allowed.

### Phase 5 — Evaluation and KTR evidence

- Add exact FTR JSON validation as a mandatory test.
- Add per-label precision/recall/F1 where ground truth exists.
- Add FPS and end-to-end latency measurement on local machine; later re-run on T4 if available.
- Add QoD selectivity metrics:
  - request rate,
  - true critical-event coverage,
  - false boost rate,
  - average boosted duration.
- Export scenario markdown and FTR-output examples for report figures.

## 6. KTR Report Filling Plan (`final_report_template.docx`)

### 1. PROJE ÖZETİ (5 puan)

Message:

- QoDe is a selective 5G-assisted road-safety inference system.
- It processes live/video input, detects vehicle metadata and risk events, and triggers QoD only when added network quality can improve analysis.
- Emphasize measurable output contract: `results.json` + API/orchestration proof.

### 2. VERİSETİ OLUŞTURULMASI (20 puan)

Include:

- Table of all support datasets and exact FTR coverage/gaps.
- Explain data balancing by target family, not only by dataset.
- Split strategy: subject/session/user grouped to avoid leakage.
- Augmentation:
  - low-light, rain/fog, blur, compression, resolution/FPS variation,
  - plate crop perspective distortion,
  - color jitter for vehicle color robustness.
- Explicitly say no single dataset covers all FTR labels; custom curation closes gaps.

### 3.1 PROBLEMİN ANALİZİ (15 puan)

Discuss:

- roadside video challenges: motion blur, glare, plate smallness, occlusion, resolution changes,
- in-cabin challenges: reflections, hand/object occlusion, small smoking/phone cues,
- temporal challenges: slalom and yawning require time windows,
- network challenge: high quality should be requested only when useful.

### 3.2 ÇÖZÜM MİMARİSİ (15 puan)

Diagram narrative:

1. mobile/video input,
2. Number Verification session gate,
3. standard-quality fast pass,
4. QoD decision policy,
5. boosted-quality detailed pass,
6. FTR output writer,
7. audit/evaluation/reporting.

Include repo components:

- `data` adapters,
- `analysis` internal contract,
- `competition` FTR contract,
- `orchestration` QoD/Number Verification flow,
- `evaluation` scenario runner,
- `local_api` demo endpoints.

### 3.3 ÇÖZÜM DETAYLARI (20 puan)

Include:

- YOLO11/RT-DETR detector details,
- PaddleOCR plate OCR and regex post-processing,
- MMAction2/VideoMAE/SlowFast action classifier plan,
- ByteTrack + geometry speed plan,
- confidence thresholding and NMS,
- Docker/runtime constraints,
- exact FTR schema validation.

### 4. ÇÖZÜMÜN SINANMASI (20 puan)

Metrics to include when models are trained:

| Task | Metrics |
| --- | --- |
| Vehicle type/color | accuracy, macro-F1 |
| Plate detection | mAP/precision/recall |
| Plate OCR | exact-match rate, regex-valid rate |
| Driver actions | per-label precision/recall/F1, temporal IoU if timestamped |
| Objects/passengers | mAP/F1 |
| Speed | MAE/RMSE if labelled |
| Runtime | FPS, p50/p95 latency, Docker runtime |
| QoD | boost request rate, critical-event coverage, false boost rate |

### 5. KAYNAKÇA (5 puan)

Use primary/official sources first:

- FTR teslim dokümantasyonu.
- 2026 teknik şartname.
- CAMARA / GSMA Number Verification and QoD docs.
- Dataset official pages.
- Model framework docs.

## 7. Remaining Blockers

External blockers:

- Turkcell Number Verification/QoD credentials, base URLs, auth flow details, profile names.
- Official final video labels and any updated evaluator schema.
- Permission/license checks for gated datasets before redistribution or public release.

Internal work still required:

- Train real model weights.
- Add Docker runtime wrapper.
- Add FTR-aligned annotations for missing labels.
- Produce final metrics and diagrams for the KTR document.
