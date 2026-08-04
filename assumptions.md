# Assumptions For Final-Stage Dataset And Competition Adaptation

This file records the repository's current reality and the assumptions that still remain explicit.

## Operating Rule

Treat every assumption below as explicit project truth until a genuinely new external input appears. When reality changes:
1. inspect the new input
2. compare it against every assumption ID below
3. keep assumptions that still hold
4. replace assumptions that are contradicted
5. record all changes in this file before changing ingestion, training, evaluation, export, or API code

## Current Source-Of-Truth Order

1. `docs/final_stage/final_yarisma_senaryosu.pdf` is authoritative for final-day operation, scoring, the 5-minute mobile recording limit, the 10-minute inference limit, and the 7 August 2026 21:00 image freeze.
2. `docs/final_stage/platform_operasyon_rehberi.pdf` is authoritative for VM/Web UI operation, the `teknofest-2026/` image prefix, and the `/app/data/input/video.mp4` → `/app/data/output/results.json` execution contract.
3. `docs/final_stage/open_gateway/` is authoritative for the organizer-provided OIDC, Number Verification, and Quality on Demand request/response contracts.
4. `docs/final_stage/open_gateway_demo_ux.pdf` is authoritative for the mobile/backend demo state flow.
5. `data/final_stage/faz2/ground_truth.json` is the golden development/evaluation fixture for the provided Faz 2 sequence; it is never a runtime sidecar for hidden/final videos.
6. `5G_ve_Yapay_Zeka_ile_Akıllı_Yol_Güvenliği_Yarışması_-_FTR_Aşaması_Teslim_D.pdf` remains authoritative for the exact FTR output schema and label vocabulary.
7. `final_report_template.docx` and the 2026 şartname remain report/background sources where they do not conflict with the final-stage sources above.
8. Local and open-source datasets are training/validation supports; they do not override the official final-stage contracts.

## Current Milestone Boundary

Implemented now:
- project assumptions registry
- dataset-manifest checker
- dataset-adapter slot and ingestion-plan bridge
- four real dataset adapters: State Farm, DMD Distraction, DMD Drowsiness, DriverSVT
- inspected real media bundle under `data/` (legacy 3-video set)
- four HuggingFace/open-source datasets downloaded and extracted under `data/datasets/`
- authoritative human-curated clip observations in `data/video_observations.json` (legacy)
- real dataset manifests for all four support datasets
- shared domain contracts
- Number Verification and QoD integration contracts with explicit mocks for offline tests; the final live-demo path now requires real organizer-provided contracts and credentials
- QoD decision simulation based on configurable policy files, retained only as a deterministic test/support path
- orchestration flow for session bootstrap, verification, analysis handoff, and QoD activation; Number Verification failure stops the live-demo flow while QoD failure must not block streaming
- deterministic scenario playback and dataset-grounded scoring harness
- markdown export and thin local HTTP wrapper for demo-oriented integration
- analysis boundary that maps all four support datasets plus the legacy clip observations into the stable orchestration contract
- `main.py`/`Dockerfile` FTR entry-point wrapper that uses explicit sidecar metadata or curated local samples and fails loudly when trained arbitrary-video inference is unavailable
- tracked Mermaid architecture sources under `docs/diagrams/`, rendered diagram PNGs, and KTR v1 report appendices with code snippets as images

**FTR inference pipeline (fully integrated as of June 2026):**
- `main.py` — full video-to-`results.json` pipeline with temporal smoothing and confidence gating
- `model_inference.py` — `SceneAnalysisEngine` with YOLO11x + EfficientNet-B2 (driver) + EfficientNet-B0 (vehicle type) + EasyOCR
- `yolcular` category: geometrically detected from YOLO person bboxes inside vehicle zones (`arka_koltuk_1`, `arka_koltuk_2`, `on_koltuk`)
- `emniyet_kemeri_ihlali`: Canny + Hough line seatbelt strap heuristic on driver crop
- `nesneler`: YOLO COCO `cell phone` (→ `teknocan`) and `laptop` (→ `bilgisayar`) classes
- `sofor_eylemi`: 4 active classes from MobileNetV3 classifier (trained on ~5000 State Farm images with windshield simulation)
- vehicle colour: K-Means dominant-colour (k=3) on centre crop, mapped to FTR 9-colour palette
- plate OCR: EasyOCR `tr+en`, Turkish plate regex validation, `"tespit_edilemedi"` sentinel on failure
- FTR schema validation: `PYTHONPATH=src python -m smart_road_safety.cli validate-ftr-output` → **PASS**

**Training pipeline (ready to run, not yet executed at full scale):**
- `preprocess_state_farm.py` — maps all ~22k State Farm FTR-relevant images with windshield augmentation
- `train_classifier.py` — EfficientNet-B2, 20 epochs, WeightedRandomSampler, CosineAnnealingLR, progressive unfreezing
- `train_vehicle_type_classifier.py` — EfficientNet-B0 for 7 FTR vehicle type classes (data collection pending)

**Packaging:**
- `Dockerfile` — `nvidia/cuda:12.1.0-base-ubuntu22.04`, builds fully offline (YOLO11x and EasyOCR downloaded at build time), FTR I/O paths (`/app/data/input/`, `/app/data/output/`)
- `requirements.txt` — EasyOCR (replaced PaddleOCR which was macOS-incompatible), torch, torchvision
- model weights excluded from git (>100 MB); downloaded at build time or trained locally

New FTR/KTR reality:
- The required `results.json` contract is not the internal orchestration contract. It must contain `video_id`, an `arac_bilgisi` object, and a `tespitler` array.
- `arac_bilgisi` fields are: `tip`, `plaka`, `renk`, `confidence_score`.
- Allowed vehicle `tip` values are: `sedan`, `suv`, `hatchback`, `pickup`, `minibus`, `panelvan`, `kamyon`.
- `plaka` must match the Turkish plate regex described in the FTR document, normalized without invalid Turkish characters or spaces that break the regex. When OCR fails, `"tespit_edilemedi"` is the accepted sentinel.
- Allowed vehicle `renk` values are: `beyaz`, `siyah`, `gri`, `kirmizi`, `mavi`, `sari`, `yesil`, `turuncu`, `kahverengi`.
- `tespitler` entries require `zaman_saniye`, `kategori`, `etiket`, `confidence_score`.
- Allowed `kategori` values are: `sofor_eylemi`, `nesneler`, `yolcular`.
- Allowed `sofor_eylemi` labels are: `arkaya_bakma`, `esneme`, `sigara_icme`, `su_icme`, `telefonla_konusma`, `slalom`, `etrafa_bakinma`, `emniyet_kemeri_ihlali`.
- Allowed `nesneler` labels are: `teknocan`, `bilgisayar`.
- Allowed `yolcular` labels are: `arka_koltuk_1`, `arka_koltuk_2`, `on_koltuk`.
- All output keys and labels must be exact, lowercase where specified, and ASCII-safe.
- The final Docker execution contract is `/app/data/input/video.mp4` input and `/app/data/output/results.json` output; model weights are stored under `/app/weights/`; runtime budget is 10 minutes on NVIDIA Tesla T4-class evaluation hardware.
- Final evaluation is Web UI-driven. CLI execution remains a development aid and is not an accepted substitute for the judge-operated Web UI flow.
- Final image names must start with `teknofest-2026/`; only one frozen final image should remain visible for judging.
- The final mobile demo requires Number Verification, an optional-success QoD request, complete HLS capture/export to MP4 within 5 minutes, backend upload, and display of the resulting `results.json`.

Available support data in the current delivery:
- State Farm Distracted Driver: 22,424 labelled train images, 79,726 unlabeled test images, 10 classes, 26 labelled train drivers
- DMD Distraction: 3 multi-camera video sessions with OpenLABEL frame-level distraction annotations
- DMD Drowsiness: 4 multi-camera video sessions with OpenLABEL frame-level drowsiness annotations
- DriverSVT: 17,561,501 telemetry rows from 633 drivers with 9 dangerous-state labels
- Legacy TOGG-like 3-video bundle with clip-level observations for vehicle presence, plate visibility, smoking, phone use, and erratic/slalom-like driving
- Organizer-provided Faz 2 HLS VOD with 240p and 1080p variants plus `data/final_stage/faz2/ground_truth.json`, containing one vehicle summary and 34 event-level FTR annotations across `sofor_eylemi`, `nesneler`, and `yolcular`

Unavailable in the current delivery:
- organizer-issued `client_id`, `client_secret`, approved redirect URI, final SIM/device binding, and live proof of Number Verification/QoD
- team VM/IP/port provisioning details required for the OIDC callback and Web UI rehearsal
- hidden final-day video ground truth, official timestamp-matching tolerance, and the exact allocation of the remaining live-demo points
- a Lifebox automation API/credential; until one is supplied, sharing remains an explicit device share-sheet/manual handoff
- official train/validation/test split metadata for DMD and DriverSVT
- labelled test ground truth for State Farm
- FTR-aligned open labels for vehicle color, exact vehicle body type, Turkish plate text, `teknocan`, `bilgisayar`, and passenger-seat occupancy in the current primary support datasets
- official DriverSVT speed unit documentation beyond the numeric `speed` telemetry column
- final deep-learning model weights, full benchmark metrics, and FPS/runtime tables for arbitrary organizer videos; lightweight reproducible report baselines are implemented

## Assumption Registry

| ID | Domain | Current Assumption | Confidence | Verify When Data Arrives | Impact Surface |
| --- | --- | --- | --- | --- | --- |
| DS-001 | dataset packaging | The project has support datasets plus an organizer-provided Faz 2 HLS VOD with 240p/1080p variants and event-level FTR ground truth. Hidden final videos remain evaluator inputs and must not depend on the Faz 2 fixture at runtime. | high | verified from the final scenario and supplied Faz 2 ground truth | dataset ingestion, preprocessing, evaluation, report wording |
| DS-002 | sample unit | Internal support sample units vary by dataset, but final FTR inference sample unit is exactly one video at `/app/data/input/video.mp4`. | high | verified from FTR Docker contract | adapters, batching, submission wrapper |
| DS-003 | annotation source | Support annotations retain their native formats; the Faz 2 fixture uses a validated `ftr_results_json` event document. Final predictions must use the exact same FTR schema but must be produced from video inference rather than by reading the fixture. | high | verified from `data/final_stage/faz2/ground_truth.json` and FTR examples | parsers, schema validation, competition exporter, leakage controls |
| DS-004 | targets | The competition target taxonomy is broader than the current driver-behavior datasets: vehicle body type, plate string, vehicle color, driver actions, selected in-cabin/road objects, and passenger positions are required output families. | high | verified from FTR expected values and şartname target list | model heads, output schema, evaluation, KTR report |
| DS-005 | plate labels | Plate detection and OCR are required. The Faz 2 GT supplies one exact Turkish plate value for development validation, but one sequence is not a reusable/general plate-training corpus; dedicated plate data and hidden-video validation remain necessary. | high | verified from the Faz 2 ground truth; revisit only if broader organizer labels arrive | OCR pipeline, post-processing, output validation |
| DS-006 | speed labels | The şartname mentions real vehicle speed as a competition data item and scoring target, but the FTR `results.json` schema currently omits a speed field. Treat speed estimation as a model/reporting objective and internal metric until an updated output schema adds a key. DriverSVT speed is telemetry-only and dataset-native. | medium | re-check if final KTR/FTR guidance revises `results.json` | normalization, reporting, optional model head |
| DS-007 | in-cabin labels | The Faz 2 GT demonstrates all required driver, `teknocan`/`bilgisayar`, and passenger-position labels, while support datasets still cover only subsets. The GT is suitable for calibration/evaluation, not unrestricted training claims. | high | verified from the 34-event Faz 2 GT | classification schema, dataset gap analysis, evaluation |
| DS-008 | annotation granularity | Support granularity varies. The Faz 2 and final output unit is a per-video vehicle summary plus event-level detections with `zaman_saniye`; repeated labels at different timestamps remain distinct events. | high | verified from the Faz 2 GT and FTR output examples | temporal logic, metrics, adapter outputs |
| DS-009 | split strategy | Support validation stays grouped by subject/session. If Faz 2 windows are used for fine-tuning, those windows cannot also enter the reported holdout; single-clip metrics are named development calibration rather than hidden-final generalization. | high | update if organizer publishes an official split | experimentation workflow, leakage controls, evaluation evidence |
| DS-010 | target-vehicle scope | Vehicle/plate/video analysis remains the AI output scope, while Number Verification, QoD, streaming, upload, and result display are separate but equally real final live-demo responsibilities. | high | verified from the final scenario and UX guide | detection logic, model roadmap, demo architecture, report wording |
| DS-011 | final-stage scope | Number Verification and QoD are no longer optional support-only paths: NV gates the live demo and QoD can add points, while QoD failure must allow streaming to continue. Mocks remain test doubles only. | high | verified from the final scenario and Open Gateway documents | orchestration, mobile, backend, reporting, live demo |
| DS-012 | report evidence | The KTR report evidence must center on FTR output compliance, dataset construction, trained model artifacts, model metrics, FPS/runtime measurements where available, Mermaid architecture sources with rendered diagrams, and source-code traceability appendices as images. | high | update when trained deep-learning weights and official evaluator outputs are available | training, evaluation, report generation |
| DS-013 | telecom integration | Official API root, OIDC flow, scopes, NV and QoD payloads are available. Only live credentials, approved redirect URI, SIM/device binding, and environment proof remain external provisioning blockers. | high | update when organizer credentials and VM callback details are delivered | mobile/auth integration, backend, live smoke |
| DS-014 | report generator | The report generator must produce a `final_report_template.docx`-aligned `ktr_v1.docx`, markdown QA artifact, evidence JSON, rendered Mermaid-backed architecture sections, and image-based code appendices from repo-grounded evidence without inventing unavailable model results. | high | verify with DOCX text extraction/rendering and generated artifact checks | reporting, tests, manual QA |
| DS-015 | evaluation focus | Final evaluation weights low-resolution inference, high-resolution inference, live demo, and presentation equally. AI metrics, <10-minute runtime, NV/QoD behavior, <5-minute mobile MP4 export, Web UI operation, and evidence quality are all acceptance concerns. | high | verified from the final scenario and platform guide | roadmap prioritization, evaluation, operations, presentation |
| DS-016 | privacy and sharing | Organizer-provided 5G network details, video files, training material, Q&A content, and evaluation data must not be shared outside the competition without Turkcell permission. | high | verified from şartname participation/privacy rule | repo hygiene, publication, data handling |
| DS-017 | final platform operation | Judges run the image through Web UI, not CLI; image names must begin with `teknofest-2026/`, the image must honor fixed FTR I/O paths, and only one frozen final image should remain. | high | verified from the platform operation guide | Docker, deployment, manual QA |
| DS-018 | final timing | Mobile HLS capture/export must complete within 5 minutes; each judged inference must complete within 10 minutes; the frozen AI image must be identified by SHA256 before 7 August 2026 21:00. | high | verified from the final scenario | mobile, inference performance, release operations |
| OR-001 | orchestration source reference | Internal orchestration may keep a stable `source_ref`, but final submission must emit `video_id` and FTR keys rather than internal source references. | high | verified from FTR examples | orchestration inputs, competition exporter |
| OR-002 | orchestration risk labels | Mobile-facing labels may remain richer internally, but any competition export must map to the exact FTR label set and reject unmapped labels rather than silently emitting unsupported names. | high | verified from FTR exact-match warning | mobile output, reporting, evaluation |
| OR-003 | orchestration identifiers | Real session IDs, API references, and QoS profile IDs will follow Turkcell/CAMARA environment formats; local deterministic IDs are acceptable only for mocks and tests. | high | inspect API environment details | orchestration traces, logging |
| EV-001 | scenario fixtures | Scenario fixtures should include both current dataset-backed demos and FTR-export validation cases, especially legacy TOGG-like video cases that can produce `results.json`. | high | update as ground truth expands | evaluation, traceability |
| EV-002 | behavior scoring | Existing dataset-grounded scoring remains useful for support-data experiments, but FTR scoring must validate exact labels, plate regex, confidence ranges, and event timestamps. | high | update when official evaluator is published | evaluation, reporting |
| EV-003 | scenario coverage | Coverage must demonstrate all major FTR families: vehicle info, plate handling, driver actions, objects, passengers, schema validation, and failure handling. | high | update as evaluation criteria evolve | evaluation, robustness |
| EX-001 | markdown exports | Judge-friendly markdown remains useful, but KTR/FTR reporting also needs tables for dataset balance, model metrics, FPS, confidence thresholds, and Docker/runtime conformance. | high | compare generated report material against `final_report_template.docx` | reporting, presentation |
| API-001 | local http wrapper | The current HTTP server is a local demo/development surface. It should expose competition-output generation/validation for local QA, but it is not the final production mobile backend. | high | replace with final integration strategy if required | demo integration, mobile client |
| API-002 | local endpoint payloads | Local API payloads may reuse internal contracts, but FTR-facing endpoints and CLI commands must speak `results.json` schema exactly. | high | inspect final mobile/backend boundaries | mobile integration, local API |
| AN-001 | analyzer inputs | Dataset-backed analysis can draw from the support datasets and legacy videos, but final inference must accept arbitrary organizer video input and produce FTR results without relying on dataset identity. | high | update after trained inference implementation | analysis boundary, model integration |
| AN-002 | analyzer outputs | The internal `AnalysisResult` remains useful for orchestration and QoD, but a separate FTR competition output contract is required for `results.json`. | high | verified from FTR schema mismatch | orchestration integration, local API, CLI |
| AN-003 | analysis session controls | Local boolean controls for verification/QoD remain deterministic demo controls only. They must not appear in the Dockerized final inference path or be used to detect evaluation environment. | high | verified from FTR anti-manipulation rule | demo flow, local API, submission wrapper |

## Observed Dataset Reality In The Current Delivery

### Support Datasets (Training / Validation / Ablation)

**State Farm Distracted Driver Detection:**
- 22,424 training images across 10 classes: safe_driving, texting_right, texting_left, phone_right, phone_left, operating_radio, drinking, reaching_behind, hair_and_makeup, talking_to_passenger
- 79,726 unlabeled test images
- 26 labelled train drivers; official test images are unlabeled, so validation should be grouped by subject
- Image format: JPEG, dashboard camera perspective
- FTR coverage: phone use, drinking/su_icme proxy, looking/reaching proxies; no vehicle type/color/plate/passenger/teknocan/bilgisayar labels

**DMD Distraction (3 sessions):**
- Multi-camera: face, body, hands (1280×720 RGB, Intel RealSense)
- OpenLABEL JSON annotations with per-frame action labels
- Actions include gaze_on_road, safe_drive, talking, phonecall, texting, drinking, reach_side, reach_backseat, hair_and_makeup, radio, hand-wheel states
- Total: ~22,263 annotated frames across 3 sessions
- FTR coverage: phone, water/drinking proxy, looking-away/reaching proxies; no vehicle info or passenger/object labels

**DMD Drowsiness (4 sessions):**
- Same multi-camera setup as DMD Distraction
- OpenLABEL JSON annotations with per-frame drowsiness labels
- Actions include eyes_state, blinks/blinking, yawning with/without hand
- Total: ~21,583 annotated frames across 4 sessions
- FTR coverage: `esneme`/drowsiness support; no vehicle info or passenger/object labels

**DriverSVT (Smartphone-Measured Vehicle Telemetry):**
- 17,561,501 rows from 633 drivers
- 40 CSV columns including the row index, speed, gforce, perclos, head_pose, mouth_open_ratio, heart_rate
- IMU data: accelerometer, gyroscope, magnetometer (raw and processed)
- 9 dangerous states: Normal, Camera off, Distraction, Unfastened belt, Drowsiness, No attention, Using phone, Eating, Smoking
- FTR coverage: telemetry support for slalom/unsafe state, phone, drowsiness, smoking, seatbelt; not direct visual vehicle/plate output

### Legacy Media Bundle (Secondary But FTR-Relevant)

- root folder contains exactly three MP4 files: `video_1.mp4`, `video_2.mp4`, `video_3.mp4`
- the previously assumed companion `snap_from_video_*` PNG folders are not present in the tracked delivery; inventory must therefore use the MP4 as `primary_source_ref` and must not invent screenshot paths
- `data/video_observations.json` is the authoritative observation layer for the three videos
- FTR coverage: TOGG-like vehicle approach, plate visibility, smoking, phone use, and erratic/slalom-like behavior; it still lacks exact plate text, vehicle type/color labels, passenger positions, `teknocan`, and `bilgisayar`

### Faz 2 Final-Stage Fixture

- `data/final_stage/faz2/ground_truth.json` contains one `suv`/`siyah`/`34TC8532` vehicle summary and 34 valid event records
- the organizer HLS master exposes 240p and 1080p VOD variants; media files are reproducible local artifacts and remain ignored by git
- the fixture covers `sofor_eylemi`, `nesneler`, and `yolcular`, but it is a single sequence and cannot establish hidden-final generalization
- the fixture is development/evaluation data only and may not be automatically loaded by final runtime inference

## Known Unavailable Inputs In The Current Delivery

- operator credentials, SIM/device binding, and live QoD/Number Verification environment details
- approved callback/redirect URI and team VM network details
- official hidden final-video labels and scoring/timestamp tolerance
- FTR-aligned annotations for vehicle body type, vehicle color, exact plate text, passengers, `teknocan`, and `bilgisayar`
- final trained deep-learning model weights and measured accuracy/FPS tables; lightweight baseline model artifacts are available for KTR evidence
- official speed-output key in FTR `results.json`

## Adaptation Checklist For Future Work

1. Keep this assumptions file aligned before changing ingestion, model, evaluation, or export code.
2. Validate every FTR-facing output against exact keys, labels, ASCII constraints, plate regex, confidence ranges, and timestamp types.
3. Keep support-dataset adapters useful for training and ablations, but do not claim they fully match FTR.
4. Add or curate FTR-aligned vehicle/plate/color/object/passenger data before training final heads.
5. Treat Number Verification/QoD as final live-demo paths; keep mocks isolated and explicitly selected for tests only.
6. Use the organizer-provided Open Gateway contracts now available; never commit client secrets or silently fall back to mocks when live config is missing.
7. Do not add environment-detection or evaluation-environment branching to final Docker code.
8. Keep `main.py` honest: final inference must use trained model output and must never silently fabricate FTR predictions or read the Faz 2 GT as a runtime sidecar.
9. Treat Faz 2 metrics as development calibration and keep training/holdout segments separated to avoid leakage.
10. Verify Web UI execution, image prefix, fixed I/O paths, timing limits, and frozen SHA256 before declaring final readiness.

## Recommended Update Style

For each changed assumption, preserve the original ID and replace only the statement, confidence, and impact notes. That makes downstream AI-assisted adaptation easier to trace.
