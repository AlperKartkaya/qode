# Assumptions For KTR/FTR Dataset And Competition Adaptation

This file records the repository's current reality and the assumptions that still remain explicit.

## Operating Rule

Treat every assumption below as explicit project truth until a genuinely new external input appears. When reality changes:
1. inspect the new input
2. compare it against every assumption ID below
3. keep assumptions that still hold
4. replace assumptions that are contradicted
5. record all changes in this file before changing ingestion, training, evaluation, export, or API code

## Current Source-Of-Truth Order

1. `5G_ve_Yapay_Zeka_ile_Akıllı_Yol_Güvenliği_Yarışması_-_FTR_Aşaması_Teslim_D.pdf` is the authoritative output-schema and packaging source for the current FTR/KTR implementation path.
2. `2026_5G_YAPAY_ZEKA_İLE_AKILLI_YOL_GÜVENLİĞİ_YARISMASI_SARTNAMESI_2_PORZ6.pdf` is the authoritative competition-scope, scoring, API-use, and privacy source.
3. Local datasets and open-source datasets are training/validation supports; they do not override the required FTR output labels or final evaluation contract.
4. `final_report_template.docx` is the authoritative report outline for the next written deliverable.

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
- Number Verification and QoD integration contracts with explicit mocks for unavailable credentials/endpoints
- QoD decision simulation based on configurable policy files
- orchestration flow for session bootstrap, verification, analysis handoff, and QoD activation
- deterministic scenario playback and dataset-grounded scoring harness
- markdown export and thin local HTTP wrapper for demo-oriented integration
- analysis boundary that maps all four support datasets plus the legacy clip observations into the stable orchestration contract

New FTR/KTR reality:
- The required `results.json` contract is not the internal orchestration contract. It must contain `video_id`, an `arac_bilgisi` object, and a `tespitler` array.
- `arac_bilgisi` fields are: `tip`, `plaka`, `renk`, `confidence_score`.
- Allowed vehicle `tip` values are: `sedan`, `suv`, `hatchback`, `pickup`, `minibus`, `panelvan`, `kamyon`.
- `plaka` must match the Turkish plate regex described in the FTR document, normalized without invalid Turkish characters or spaces that break the regex.
- Allowed vehicle `renk` values are: `beyaz`, `siyah`, `gri`, `kirmizi`, `mavi`, `sari`, `yesil`, `turuncu`, `kahverengi`.
- `tespitler` entries require `zaman_saniye`, `kategori`, `etiket`, `confidence_score`.
- Allowed `kategori` values are: `sofor_eylemi`, `nesneler`, `yolcular`.
- Allowed `sofor_eylemi` labels are: `arkaya_bakma`, `esneme`, `sigara_icme`, `su_icme`, `telefonla_konusma`, `slalom`, `etrafa_bakinma`, `emniyet_kemeri_ihlali`.
- Allowed `nesneler` labels are: `teknocan`, `bilgisayar`.
- Allowed `yolcular` labels are: `arka_koltuk_1`, `arka_koltuk_2`, `on_koltuk`.
- All output keys and labels must be exact, lowercase where specified, and ASCII-safe.
- The final Docker execution contract is `/app/data/input/video.mp4` input and `/app/data/output/results.json` output; model weights should be packaged under `/app/models/`; runtime budget is 10 minutes on NVIDIA Tesla T4-class evaluation hardware.

Available support data in the current delivery:
- State Farm Distracted Driver: 22,424 labelled train images, 79,726 unlabeled test images, 10 classes, 26 labelled train drivers
- DMD Distraction: 3 multi-camera video sessions with OpenLABEL frame-level distraction annotations
- DMD Drowsiness: 4 multi-camera video sessions with OpenLABEL frame-level drowsiness annotations
- DriverSVT: 17,561,501 telemetry rows from 633 drivers with 9 dangerous-state labels
- Legacy TOGG-like 3-video bundle with clip-level observations for vehicle presence, plate visibility, smoking, phone use, and erratic/slalom-like driving

Unavailable in the current delivery:
- official telecom API credentials, sandbox base URLs, client IDs/secrets, and SIM/device binding details
- official FTR test-video ground-truth labels beyond the three local observed videos
- official train/validation/test split metadata for DMD and DriverSVT
- labelled test ground truth for State Farm
- FTR-aligned open labels for vehicle color, exact vehicle body type, Turkish plate text, `teknocan`, `bilgisayar`, and passenger-seat occupancy in the current primary support datasets
- official DriverSVT speed unit documentation beyond the numeric `speed` telemetry column
- trained model weights and benchmark metrics for the final KTR report

## Assumption Registry

| ID | Domain | Current Assumption | Confidence | Verify When Data Arrives | Impact Surface |
| --- | --- | --- | --- | --- | --- |
| DS-001 | dataset packaging | The project has support datasets for driver behavior and telemetry plus a legacy three-video TOGG-like bundle; the final competition evaluator will run on organizer-provided videos, not on these support datasets directly. | high | verified from FTR and şartname: open-source datasets are allowed, but extra organizer training data beyond sample videos will not be shared | dataset ingestion, preprocessing, report wording |
| DS-002 | sample unit | Internal support sample units vary by dataset, but final FTR inference sample unit is exactly one video at `/app/data/input/video.mp4`. | high | verified from FTR Docker contract | adapters, batching, submission wrapper |
| DS-003 | annotation source | Support annotations come from State Farm folder/CSV labels, DMD OpenLABEL JSON, DriverSVT dangerousstate CSV labels, and legacy clip observations; final FTR labels must be produced in the exact `results.json` schema regardless of source annotation names. | high | verified from FTR output examples | parsers, schema validation, competition exporter |
| DS-004 | targets | The competition target taxonomy is broader than the current driver-behavior datasets: vehicle body type, plate string, vehicle color, driver actions, selected in-cabin/road objects, and passenger positions are required output families. | high | verified from FTR expected values and şartname target list | model heads, output schema, evaluation, KTR report |
| DS-005 | plate labels | Plate detection and OCR are required for the FTR output. Current local support datasets do not provide reusable plate-text labels; the legacy media only marks plate visibility. A dedicated plate detector/OCR dataset or synthetic/curated Turkish-plate augmentation is required. | high | update only if organizer publishes labelled plate ground truth | OCR pipeline, post-processing, output validation |
| DS-006 | speed labels | The şartname mentions real vehicle speed as a competition data item and scoring target, but the FTR `results.json` schema currently omits a speed field. Treat speed estimation as a model/reporting objective and internal metric until an updated output schema adds a key. DriverSVT speed is telemetry-only and dataset-native. | medium | re-check if final KTR/FTR guidance revises `results.json` | normalization, reporting, optional model head |
| DS-007 | in-cabin labels | FTR in-cabin/action coverage is narrower and label-specific: `sigara_icme`, `telefonla_konusma`, `su_icme`, `esneme`, `arkaya_bakma`, `etrafa_bakinma`, `emniyet_kemeri_ihlali`, `slalom`, plus `teknocan`, `bilgisayar`, and passenger-seat positions. Existing datasets cover only a subset and need mapping plus gap-specific data. | high | verified from FTR labels and current manifests | classification schema, dataset gap analysis |
| DS-008 | annotation granularity | Support granularity remains per-image, frame-level, row-level, or clip-level depending on dataset. Final output granularity is event-level with `zaman_saniye` for every detection plus one per-video vehicle summary. | high | verified from FTR output examples | temporal logic, metrics, adapter outputs |
| DS-009 | split strategy | State Farm validation should be grouped by subject; DMD and DriverSVT splits should be grouped by subject/user; final validation should additionally include a KTR holdout of legacy/curated videos rendered into FTR `results.json` outputs. | high | update if organizer publishes official validation split | experimentation workflow, KTR evidence |
| DS-010 | TOGG trigger | TOGG/target-vehicle approach is again a primary competition use case for QoD triggering. Driver-behavior-only datasets are not sufficient to prove the full yarışma scope. | high | verified from şartname purpose and QoD scenario wording | trigger policy, detection logic, model roadmap |
| DS-011 | quality modes | The system must preserve at least two network-quality states: standard/best-effort analysis and QoD-boosted analysis after a critical scene trigger. | high | inspect final API docs and live environment | simulation, mobile flow, report architecture |
| DS-012 | QoD policy | QoD should be requested only when there is an observable benefit: TOGG approach, plate readability need, driver-risk/in-cabin detail need, or other critical scene context. | high | verified from şartname QoD scoring description; calibrate with live API later | trigger policy, scoring, report |
| DS-013 | Number Verification integration | Real Number Verification credentials and Turkcell environment details are not present. Keep mock behavior isolated, but design against CAMARA/Open Gateway semantics: silent SIM/phone-number verification over mobile data before session use. | high | update when Turkcell credentials/base URL/device details are granted | mobile/auth integration |
| DS-014 | QoD API integration | Real QoD credentials/base URL are not present. Keep mock behavior isolated, but design against CAMARA/Open Gateway semantics: create/manage a temporary QoS session for the video/data flow only when policy says the scene is critical. | high | update when Turkcell credentials/base URL/QoS profile names are granted | API client, orchestration |
| DS-015 | evaluation focus | Final/KTR evaluation must emphasize three axes: AI accuracy/precision for FTR labels, selective QoD/API integration, and modern software architecture/report quality. | high | verified from şartname scoring table | roadmap prioritization, KTR sections |
| DS-016 | privacy and sharing | Organizer-provided 5G network details, video files, training material, Q&A content, and evaluation data must not be shared outside the competition without Turkcell permission. | high | verified from şartname participation/privacy rule | repo hygiene, publication, data handling |
| OR-001 | orchestration source reference | Internal orchestration may keep a stable `source_ref`, but final submission must emit `video_id` and FTR keys rather than internal source references. | high | verified from FTR examples | orchestration inputs, competition exporter |
| OR-002 | orchestration risk labels | Mobile-facing labels may remain richer internally, but any competition export must map to the exact FTR label set and reject unmapped labels rather than silently emitting unsupported names. | high | verified from FTR exact-match warning | mobile output, reporting, evaluation |
| OR-003 | orchestration identifiers | Real session IDs, API references, and QoS profile IDs will follow Turkcell/CAMARA environment formats; local deterministic IDs are acceptable only for mocks and tests. | high | inspect API environment details | orchestration traces, logging |
| EV-001 | scenario fixtures | Scenario fixtures should include both current dataset-backed demos and FTR-export validation cases, especially legacy TOGG-like video cases that can produce `results.json`. | high | update as ground truth expands | evaluation, traceability |
| EV-002 | behavior scoring | Existing dataset-grounded scoring remains useful for support-data experiments, but FTR scoring must validate exact labels, plate regex, confidence ranges, and event timestamps. | high | update when official evaluator is published | evaluation, reporting |
| EV-003 | scenario coverage | Coverage must demonstrate all major FTR families: vehicle info, plate handling, driver actions, objects, passengers, QoD trigger/selectivity, and failure handling. | high | update as evaluation criteria evolve | evaluation, robustness |
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
- each video has a companion screenshot folder: `snap_from_video_1/`, `snap_from_video_2/`, `snap_from_video_3/`
- each screenshot folder currently contains four PNG still images
- `data/video_observations.json` is the authoritative observation layer for the three videos
- FTR coverage: TOGG-like vehicle approach, plate visibility, smoking, phone use, and erratic/slalom-like behavior; it still lacks exact plate text, vehicle type/color labels, passenger positions, `teknocan`, and `bilgisayar`

## Known Unavailable Inputs In The Current Delivery

- official telecom API docs beyond public CAMARA/Open Gateway references and high-level competition wording
- operator credentials, SIM/device binding, and live QoD/Number Verification environment details
- official final test-video labels
- FTR-aligned annotations for vehicle body type, vehicle color, exact plate text, passengers, `teknocan`, and `bilgisayar`
- trained model weights and measured accuracy/FPS tables
- official speed-output key in FTR `results.json`

## Adaptation Checklist For Future Work

1. Keep this assumptions file aligned before changing ingestion, model, evaluation, or export code.
2. Validate every FTR-facing output against exact keys, labels, ASCII constraints, plate regex, confidence ranges, and timestamp types.
3. Keep support-dataset adapters useful for training and ablations, but do not claim they fully match FTR.
4. Add or curate FTR-aligned vehicle/plate/color/object/passenger data before training final heads.
5. Keep QoD thresholds configurable; do not bury dataset-specific constants inside model code.
6. Keep telecom mocks isolated behind gateway interfaces until real credentials and base URLs are provided.
7. Do not add environment-detection or evaluation-environment branching to final Docker code.

## Recommended Update Style

For each changed assumption, preserve the original ID and replace only the statement, confidence, and impact notes. That makes downstream AI-assisted adaptation easier to trace.
