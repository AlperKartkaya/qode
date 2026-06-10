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
- inspected real media bundle under `data/`
- authoritative human-curated clip observations in `data/video_observations.json`
- shared domain contracts
- Number Verification and QoD integration contracts
- QoD decision simulation based on configurable policy files
- mock orchestration flow for session bootstrap, verification, analysis handoff, and QoD activation
- deterministic scenario playback and placeholder scoring harness
- markdown export and thin local HTTP wrapper for demo-oriented integration
- analysis boundary backed by the delivered media bundle and the authoritative clip observation registry
- real mixed-media dataset inventory for the delivered bundle under `data/`

Unavailable in the current final delivery:
- official telecom API details and credentials
- structured speed ground truth
- official train/validation/test split metadata
- machine-generated structured annotation files beyond the curated observation registry

## Assumption Registry

| ID | Domain | Current Assumption | Confidence | Verify When Data Arrives | Impact Surface |
| --- | --- | --- | --- | --- | --- |
| DS-001 | dataset packaging | The offline development dataset will contain video files, not only extracted images. | high | verified: MP4 files observed in data directory | dataset ingestion, preprocessing |
| DS-002 | sample unit | The currently delivered dataset is a mixed media bundle organized around three MP4 videos with companion screenshot folders, so the practical unit is `video clip + extracted stills` rather than a pure video-only or image-only sample. | high | verified: media bundle matches this description | adapters, evaluation, batching |
| DS-003 | annotation source | The final dataset uses a repository-local human-curated clip observation registry in `data/video_observations.json` because no official structured sidecar annotations or docs were delivered. | high | verified: no external annotations found | parsers, schema validation |
| DS-004 | targets | The final supported outputs are vehicle presence, plate visibility, in-cabin cues, and driver-behavior risk labels derived from the three authoritative clip observations; speed is unavailable and optional. | high | update only if the project scope or external inputs truly change | task routing, model heads |
| DS-005 | plate labels | Plate visibility is supported as an observed cue, while explicit plate text remains optional and is not required by the current pipeline. | high | update only if an authoritative plate-text source appears | OCR pipeline, post-processing |
| DS-006 | speed labels | Speed ground truth is unavailable in the final delivery and is treated as out of scope rather than a blocker. | high | update only if an authoritative speed source appears | normalization, reporting |
| DS-007 | in-cabin labels | In-cabin smoking and phone-use cues are provided through the authoritative clip observation registry rather than external annotation files. | high | update only if a richer in-cabin taxonomy appears | classification schema, UI labels |
| DS-008 | annotation granularity | The final annotation granularity is clip-level human observation keyed by video sample. | high | update only if a richer temporal labeling source appears | adapters, metrics, temporal smoothing |
| DS-009 | split strategy | The delivered dataset is a fixed three-sample media set and is not expected to gain official train/validation/test splits. | high | update only if the project scope changes to training on additional data | experimentation workflow |
| DS-010 | TOGG trigger | The three delivered videos all center on the target TOGG vehicle approaching the camera, and the current project may treat target-vehicle presence as an authoritative clip fact. | high | update only if additional clips introduce ambiguity | trigger policy, detection logic |
| DS-011 | quality modes | There will be at least two meaningful video-quality states in practice: normal quality and boosted quality after QoD. | high | inspect stream setup or final API docs | simulation, mobile flow |
| DS-012 | QoD policy | QoD should be requested only when there is an observable benefit such as approach detection, plate-read need, or driver-risk review. | high | confirm against final API docs and judging guidance | trigger policy |
| DS-013 | Number Verification integration | Real Number Verification behavior remains unavailable, so the repository will keep explicit mock-backed behavior for this interface. | high | update only if operator access is separately granted | mobile/auth integration |
| DS-014 | QoD API integration | Real QoD endpoint details remain unavailable, so the repository will keep explicit mock-backed QoD activation behavior. | high | update only if operator access is separately granted | API client, orchestration |
| DS-015 | evaluation focus | Final evaluation will favor a balance of AI accuracy, selective QoD usage, and overall architecture quality rather than raw model complexity alone. | high | compare against final judging and report guidance | roadmap prioritization |
| DS-016 | privacy and sharing | Dataset and network details provided during the competition should be treated as non-public unless clearly stated otherwise. | high | inspect NDA, sharing rules, or package notices | repo hygiene, deployment |
| OR-001 | orchestration source reference | The orchestration input will carry a stable `source_ref` string for each analyzed item, but the final identifier format is unknown until the dataset or live stream contracts are released. | medium | inspect dataset sample identifiers and live stream metadata | orchestration inputs, mobile display |
| OR-002 | orchestration risk labels | The mobile-facing analysis summary uses the current authoritative risk taxonomy: `smoking_and_unsafe_scanning`, `phone_use_while_driving`, and `drunk_like_erratic_driving`. | high | update only if the project taxonomy intentionally changes | mobile output, reporting |
| OR-003 | orchestration identifiers | Real session IDs and network request references will likely follow operator-specific formats, so current mock orchestration uses deterministic local placeholder strings only. | high | inspect Number Verification and QoD environment details | orchestration traces, logging |
| EV-001 | scenario fixtures | The scenario fixtures are now keyed to the three real delivered videos and their authoritative clip observations. | high | update only if the scenario set itself changes | evaluation, traceability |
| EV-002 | behavior scoring | Current label agreement metrics measure agreement against authoritative human-curated behavior observations, not model-generated predictions or external labels. | high | update only if a new scoring source is intentionally introduced | evaluation, reporting |
| EV-003 | scenario coverage | The scenario set intentionally covers the three delivered videos only; no additional dataset-driven cases are expected from this delivery. | high | update only if the dataset itself changes | evaluation, robustness |
| EX-001 | markdown exports | Judge-friendly markdown is generated from the current scenario report JSON contract, so any future report schema change must update the export renderer too. | medium | compare markdown needs against final report and presentation expectations | reporting, presentation |
| API-001 | local http wrapper | The current HTTP server is a local stdlib wrapper for demos and mobile prototyping only, not a production deployment surface. | high | replace with final client/server integration strategy if the competition setup requires it | demo integration, mobile client |
| API-002 | local endpoint payloads | The local API reuses repository JSON contracts directly; final mobile-facing payloads may require reshaping once the real app and backend boundaries are known. | medium | inspect final mobile UX and telecom environment constraints | mobile integration, local API |
| AN-001 | analyzer inputs | Dataset-backed analysis now joins real media inventory with the authoritative clip observation registry instead of waiting for future structured labels. | high | update only if a new analysis source is intentionally introduced | analysis boundary, model integration |
| AN-002 | analyzer outputs | The analysis result schema is intended to remain stable even after real models arrive, with future adapters mapping model outputs into this contract. | medium | compare real model outputs and task taxonomy against the current schema | orchestration integration, local API |
| AN-003 | analysis session controls | The analysis session request uses local boolean controls for verification and QoD availability to keep demo runs deterministic until real telecom environments exist. | high | replace local controls with real environment-driven behavior when Number Verification and QoD endpoints are available | demo flow, local API |

## Observed Dataset Reality In The Current Delivery

- root folder contains exactly three MP4 files: `video_1.mp4`, `video_2.mp4`, `video_3.mp4`
- each video has a companion screenshot folder: `snap_from_video_1/`, `snap_from_video_2/`, `snap_from_video_3/`
- each screenshot folder currently contains four PNG still images
- inspected screenshots show a TOGG vehicle in an indoor parking-garage style environment
- the front plate is visually readable in inspected screenshots
- a driver is visually visible in inspected screenshots
- `data/video_observations.json` is the authoritative observation layer for the three videos

## Known Unavailable Inputs In The Final Delivery

- structured speed ground truth
- official telecom API docs, auth details, and credentials
- official train/validation/test split metadata
- external structured annotation files beyond the observation registry

## Adaptation Checklist For The Future AI Agent

1. Read the real dataset tree and the observation registry.
2. Keep `data/real_dataset_manifest.json` and `data/video_observations.json` aligned with actual project truth.
3. Update this file first if reality changes.
4. Update Python contracts only where current authoritative observations require it.
5. Keep QoD policy thresholds configurable; do not bury dataset-specific constants inside model code.

## What Should Change Immediately If Reality Differs

- If new authoritative observations appear, add them to `data/video_observations.json` and keep the same schema.
- If plate text becomes authoritative, add it explicitly rather than inferring it silently.
- If speed evidence becomes authoritative, add it as an optional capability instead of assuming it now.

## Recommended Update Style

For each changed assumption, preserve the original ID and replace only the statement, confidence, and impact notes. That makes downstream AI-assisted adaptation easier to trace.
