# Assumptions For Future Dataset Adaptation

This file records the repository's current reality and the assumptions that still remain explicit.

## Operating Rule

Treat every assumption below as explicit project truth until a genuinely new external input appears. When reality changes:
1. inspect the new input
2. compare it against every assumption ID below
3. keep assumptions that still hold
4. replace assumptions that are contradicted
5. record all changes in this file before changing ingestion, training, or evaluation code

## Current Milestone Boundary

Implemented now:
- project assumptions registry
- dataset-manifest checker
- dataset-adapter slot and ingestion-plan bridge
- four real dataset adapters: State Farm, DMD Distraction, DMD Drowsiness, DriverSVT
- inspected real media bundle under `data/` (legacy 3-video set)
- four HuggingFace datasets downloaded and extracted under `data/datasets/`
- authoritative human-curated clip observations in `data/video_observations.json` (legacy)
- real dataset manifests for all four HuggingFace datasets
- shared domain contracts
- Number Verification and QoD integration contracts
- QoD decision simulation based on configurable policy files
- mock orchestration flow for session bootstrap, verification, analysis handoff, and QoD activation
- deterministic scenario playback and dataset-grounded scoring harness
- markdown export and thin local HTTP wrapper for demo-oriented integration
- analysis boundary that maps all four primary datasets plus the legacy clip observations into the stable orchestration contract

Available in the current delivery:
- State Farm Distracted Driver: 22,424 labelled train images, 79,726 unlabeled test images, 10 classes, 26 labelled train drivers
- DMD Distraction: 3 multi-camera video sessions with OpenLABEL frame-level distraction annotations
- DMD Drowsiness: 4 multi-camera video sessions with OpenLABEL frame-level drowsiness annotations
- DriverSVT: 17,561,501 telemetry rows from 633 drivers with 9 dangerous-state labels

Unavailable in the current final delivery:
- official telecom API details and credentials
- official train/validation/test split metadata for DMD and DriverSVT
- labelled test ground truth for State Farm
- official DriverSVT speed unit documentation beyond the numeric `speed` telemetry column
- machine-generated structured annotation files beyond the datasets' own label formats

## Assumption Registry

| ID | Domain | Current Assumption | Confidence | Verify When Data Arrives | Impact Surface |
| --- | --- | --- | --- | --- | --- |
| DS-001 | dataset packaging | The project now has four distinct datasets: State Farm (JPEG images), DMD Distraction (MP4+OpenLABEL), DMD Drowsiness (MP4+OpenLABEL), and DriverSVT (CSV telemetry). The legacy 3-video bundle is retained but no longer the primary data source. | high | verified: all four datasets downloaded and inspected | dataset ingestion, preprocessing |
| DS-002 | sample unit | Sample units vary by dataset: individual images (State Farm), multi-camera video sessions (DMD), and telemetry time-series rows (DriverSVT). | high | verified: structure matches this description | adapters, evaluation, batching |
| DS-003 | annotation source | Each dataset carries its own annotation format: folder-class labels with CSV metadata (State Farm), OpenLABEL frame-level JSON (DMD), and CSV `dangerousstate` plus telemetry columns (DriverSVT). | high | verified: annotation files inspected | parsers, schema validation |
| DS-004 | targets | The unified target taxonomy now covers 10 distraction classes (State Farm), OpenLABEL distraction/drowsiness action types (DMD), and 9 dangerous states (DriverSVT). Vehicle/plate detection is no longer a required target. | high | update if competition evaluation criteria specify otherwise | task routing, model heads |
| DS-005 | plate labels | Plate detection is not applicable in the current datasets, which focus on driver behavior monitoring rather than external vehicle detection. | high | update only if the competition scope requires plate detection | OCR pipeline, post-processing |
| DS-006 | speed labels | Speed ground truth is available in DriverSVT as a numeric telemetry column, but the local dataset README does not document the physical unit; report it as dataset-native speed until official unit documentation appears. It is not available in State Farm or DMD. | high | verified: DriverSVT CSV contains speed column; unit docs absent | normalization, reporting |
| DS-007 | in-cabin labels | In-cabin behavior labels are rich across all datasets: phone use, texting, drinking, eating, smoking, radio operation, reaching, yawning, eye closure, and more. | high | verified: all datasets inspected | classification schema, UI labels |
| DS-008 | annotation granularity | Granularity varies: per-image class labels (State Farm), frame-level temporal annotations (DMD), and row-level telemetry state labels (DriverSVT). | high | update if a new labeling source appears | adapters, metrics, temporal smoothing |
| DS-009 | split strategy | State Farm has labelled train metadata with subject IDs plus an unlabeled official test image set; validation should be grouped by train subject. DMD and DriverSVT do not have official splits; custom splits should be created by subject/user ID. | high | update if official competition splits are provided | experimentation workflow |
| DS-010 | TOGG trigger | Target-vehicle detection (TOGG) is no longer the primary use case. The focus is now driver behavior monitoring across multiple contexts. The legacy TOGG videos are preserved but not the main analysis target. | high | update if the competition explicitly requires vehicle detection | trigger policy, detection logic |
| DS-011 | quality modes | There will be at least two meaningful video-quality states in practice: normal quality and boosted quality after QoD. | high | inspect stream setup or final API docs | simulation, mobile flow |
| DS-012 | QoD policy | QoD should be requested only when there is an observable benefit such as driver risk detection requiring higher quality streams, or detailed in-cabin analysis needs. | high | confirm against final API docs and judging guidance | trigger policy |
| DS-013 | Number Verification integration | Real Number Verification behavior remains unavailable, so the repository will keep explicit mock-backed behavior for this interface. | high | update only if operator access is separately granted | mobile/auth integration |
| DS-014 | QoD API integration | Real QoD endpoint details remain unavailable, so the repository will keep explicit mock-backed QoD activation behavior. | high | update only if operator access is separately granted | API client, orchestration |
| DS-015 | evaluation focus | Final evaluation will favor a balance of AI accuracy on driver behavior classification, selective QoD usage, and overall architecture quality. | high | compare against final judging and report guidance | roadmap prioritization |
| DS-016 | privacy and sharing | Dataset and network details provided during the competition should be treated as non-public unless clearly stated otherwise. | high | inspect NDA, sharing rules, or package notices | repo hygiene, deployment |
| OR-001 | orchestration source reference | The orchestration input carries a stable `source_ref` string derived from dataset sample identifiers (e.g., subject+class for State Farm, session ID for DMD, row index for DriverSVT). | medium | inspect live stream metadata if available | orchestration inputs, mobile display |
| OR-002 | orchestration risk labels | The mobile-facing analysis summary uses a unified risk taxonomy derived from the real datasets: distraction types, drowsiness indicators, and telemetry-based states. | high | update only if the project taxonomy intentionally changes | mobile output, reporting |
| OR-003 | orchestration identifiers | Real session IDs and network request references will likely follow operator-specific formats, so current mock orchestration uses deterministic local placeholder strings only. | high | inspect Number Verification and QoD environment details | orchestration traces, logging |
| EV-001 | scenario fixtures | Scenario fixtures should be expanded to cover samples from all four real datasets, not just the legacy 3-video set. | high | update as evaluation criteria are finalized | evaluation, traceability |
| EV-002 | behavior scoring | Scoring should use real dataset ground truth labels where available: labelled State Farm train classes, OpenLABEL action intervals/action sets for DMD, DriverSVT `dangerousstate`, and the legacy clip observation registry. | high | update only if a new scoring source is introduced | evaluation, reporting |
| EV-003 | scenario coverage | The scenario set should cover representative samples from each dataset to demonstrate breadth of capability. | high | update as evaluation criteria evolve | evaluation, robustness |
| EX-001 | markdown exports | Judge-friendly markdown is generated from the current scenario report JSON contract, so any future report schema change must update the export renderer too. | medium | compare markdown needs against final report and presentation expectations | reporting, presentation |
| API-001 | local http wrapper | The current HTTP server is a local stdlib wrapper for demos and mobile prototyping only, not a production deployment surface. | high | replace with final client/server integration strategy if the competition setup requires it | demo integration, mobile client |
| API-002 | local endpoint payloads | The local API reuses repository JSON contracts directly; final mobile-facing payloads may require reshaping once the real app and backend boundaries are known. | medium | inspect final mobile UX and telecom environment constraints | mobile integration, local API |
| AN-001 | analyzer inputs | Dataset-backed analysis can now draw from any of the four real datasets via the adapter system, not just the legacy clip observation registry. | high | update only if a new analysis source is intentionally introduced | analysis boundary, model integration |
| AN-002 | analyzer outputs | The analysis result schema is intended to remain stable even after real models arrive, with future adapters mapping model outputs into this contract. | medium | compare real model outputs and task taxonomy against the current schema | orchestration integration, local API |
| AN-003 | analysis session controls | The analysis session request uses local boolean controls for verification and QoD availability to keep demo runs deterministic until real telecom environments exist. | high | replace local controls with real environment-driven behavior when Number Verification and QoD endpoints are available | demo flow, local API |

## Observed Dataset Reality In The Current Delivery

### HuggingFace Datasets (Primary)

**State Farm Distracted Driver Detection:**
- 22,424 training images across 10 classes: safe_driving, texting_right, texting_left, phone_right, phone_left, operating_radio, drinking, reaching_behind, hair_and_makeup, talking_to_passenger
- 79,726 unlabeled test images
- 26 labelled train drivers; official test images are unlabeled, so train validation should be grouped by subject
- Image format: JPEG, dashboard camera perspective

**DMD Distraction (3 sessions):**
- Multi-camera: face, body, hands (1280×720 RGB, Intel RealSense)
- OpenLABEL JSON annotations with per-frame action labels
- Actions: gaze_on_road, safe_drive, talking, phonecall, texting, drinking, reach_side, reach_backseat, hair_and_makeup, radio, hand-wheel states
- Total: ~22,263 annotated frames across 3 sessions

**DMD Drowsiness (4 sessions):**
- Same multi-camera setup as DMD Distraction
- OpenLABEL JSON annotations with per-frame drowsiness labels
- Actions: eyes_state (open/close/opening/closing/undefined), blinks/blinking, yawning (with/without hand)
- Total: ~21,583 annotated frames across 4 sessions

**DriverSVT (Smartphone-Measured Vehicle Telemetry):**
- 17,561,501 rows from 633 drivers
- 40 CSV columns including the row index, speed, gforce, perclos, head_pose, mouth_open_ratio, heart_rate
- IMU data: accelerometer, gyroscope, magnetometer (raw and processed)
- 9 dangerous states: Normal (81.5%), Camera off (5.0%), Distraction (4.4%), Unfastened belt (3.3%), Drowsiness (2.9%), No attention (2.0%), Using phone (0.9%), Eating (0.1%), Smoking (<0.01%)

### Legacy Media Bundle (Secondary)

- root folder contains exactly three MP4 files: `video_1.mp4`, `video_2.mp4`, `video_3.mp4`
- each video has a companion screenshot folder: `snap_from_video_1/`, `snap_from_video_2/`, `snap_from_video_3/`
- each screenshot folder currently contains four PNG still images
- `data/video_observations.json` is the authoritative observation layer for the three videos

## Known Unavailable Inputs In The Final Delivery

- official telecom API docs, auth details, and credentials
- official train/validation/test split metadata for DMD and DriverSVT
- labelled State Farm test ground truth
- structured speed ground truth for State Farm or DMD (available only as dataset-native numeric telemetry in DriverSVT)
- official DriverSVT speed unit documentation

## Adaptation Checklist For The Future AI Agent

1. Read the real dataset tree and the observation registry.
2. Keep manifests under `data/datasets/*/manifest.json` aligned with actual project truth.
3. Update this file first if reality changes.
4. Update Python contracts only where current authoritative observations require it.
5. Keep QoD policy thresholds configurable; do not bury dataset-specific constants inside model code.

## What Should Change Immediately If Reality Differs

- If new datasets appear, create new adapters using the existing adapter-slot architecture.
- If competition evaluation criteria specify a primary dataset, prioritize that dataset in evaluation flows.
- If real telecom API details arrive, replace mock gateways with real implementations.

## Recommended Update Style

For each changed assumption, preserve the original ID and replace only the statement, confidence, and impact notes. That makes downstream AI-assisted adaptation easier to trace.
