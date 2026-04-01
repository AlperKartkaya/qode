# Assumptions For Future Dataset Adaptation

This file is intentionally written for a future AI agent or developer who will adapt the repository once the real dataset and API details are released.

## Operating Rule

Treat every assumption below as provisional. When the real dataset arrives:
1. inspect the dataset and any accompanying API documentation
2. compare reality against every assumption ID below
3. keep assumptions that still hold
4. replace assumptions that are contradicted
5. record all changes in this file before changing ingestion, training, or evaluation code

## Current Milestone Boundary

Implemented now:
- project assumptions registry
- dataset-manifest checker
- dataset-adapter slot and ingestion-plan bridge
- inspected real media bundle under `data/`
- shared domain contracts
- Number Verification and QoD integration contracts
- QoD decision simulation based on configurable policy files
- mock orchestration flow for session bootstrap, verification, analysis handoff, and QoD activation
- deterministic scenario playback and placeholder scoring harness
- markdown export and thin local HTTP wrapper for demo-oriented integration
- placeholder analysis boundary for future model outputs
- real mixed-media dataset inventory for the delivered bundle under `data/`

Deferred until real data or real API release:
- concrete dataset loader
- real model training pipeline
- OCR and speed-estimation implementation details
- production mobile client
- real Number Verification and QoD API clients

## Assumption Registry

| ID | Domain | Current Assumption | Confidence | Verify When Data Arrives | Impact Surface |
| --- | --- | --- | --- | --- | --- |
| DS-001 | dataset packaging | The offline development dataset will contain video files, not only extracted images. | high | inspect directory tree and file extensions | dataset ingestion, preprocessing |
| DS-002 | sample unit | The currently delivered dataset is a mixed media bundle organized around three MP4 videos with companion screenshot folders, so the practical unit is `video clip + extracted stills` rather than a pure video-only or image-only sample. | high | inspect whether later releases add labels keyed per video, per frame, or per extracted image | adapters, evaluation, batching |
| DS-003 | annotation source | No structured annotation files or dataset documentation were observed inside the delivered `data/` folder, so labels may be absent from this drop or delivered separately later. | high | inspect future sidecar files, docs, or external label packages | parsers, schema validation |
| DS-004 | targets | The delivered media clearly contains a vehicle and visible front plate imagery, but there is no machine-readable evidence yet for speed, in-cabin object, or driver-behavior labels. | high | compare any future label ontology or docs against the visible media and competition target list | task routing, model heads |
| DS-005 | plate labels | The front plate is visually readable in inspected screenshots, but no explicit plate text annotation file was observed. | high | inspect whether plate strings, boxes, masks, or OCR labels arrive separately | OCR pipeline, post-processing |
| DS-006 | speed labels | No speed ground-truth metadata was observed in the delivered dataset bundle. | high | inspect future metadata/docs for speed labels and units | normalization, reporting |
| DS-007 | in-cabin labels | A driver is visually visible in inspected screenshots, but no structured in-cabin object or behavior labels were observed. | medium | inspect whether future labels expose phone, cigarette, fatigue, distraction, or only raw imagery | classification schema, UI labels |
| DS-008 | annotation granularity | Annotation granularity is still unknown because the current delivery contains media only and no structured labels. | high | inspect any future labels for frame-level, clip-level, or event-level structure | adapters, metrics, temporal smoothing |
| DS-009 | split strategy | No train/validation/test split was observed in the delivered `data/` folder; the current bundle appears to be a single unsplit media set. | high | inspect whether future releases add official splits or split metadata | experimentation workflow |
| DS-010 | TOGG trigger | The inspected screenshots visually center on a TOGG vehicle, but there is no explicit machine-readable TOGG identifier yet. | medium | inspect whether future labels or metadata explicitly identify the target vehicle | trigger policy, detection logic |
| DS-011 | quality modes | There will be at least two meaningful video-quality states in practice: normal quality and boosted quality after QoD. | high | inspect stream setup or final API docs | simulation, mobile flow |
| DS-012 | QoD policy | QoD should be requested only when there is an observable benefit such as approach detection, plate-read need, or driver-risk review. | high | confirm against final API docs and judging guidance | trigger policy |
| DS-013 | Number Verification integration | Real Number Verification behavior will only be testable once Turkcell provides the final environment, so current work should use mocks or interface boundaries only. | high | inspect final environment and auth requirements | mobile/auth integration |
| DS-014 | QoD API integration | Real QoD request and response shapes are unknown for now, so current work should model intent and state transitions rather than final HTTP payloads. | high | inspect official endpoint docs, auth, and request contracts | API client, orchestration |
| DS-015 | evaluation focus | Final evaluation will favor a balance of AI accuracy, selective QoD usage, and overall architecture quality rather than raw model complexity alone. | high | compare against final judging and report guidance | roadmap prioritization |
| DS-016 | privacy and sharing | Dataset and network details provided during the competition should be treated as non-public unless clearly stated otherwise. | high | inspect NDA, sharing rules, or package notices | repo hygiene, deployment |
| OR-001 | orchestration source reference | The orchestration input will carry a stable `source_ref` string for each analyzed item, but the final identifier format is unknown until the dataset or live stream contracts are released. | medium | inspect dataset sample identifiers and live stream metadata | orchestration inputs, mobile display |
| OR-002 | orchestration risk labels | The mobile-facing analysis summary will expose a normalized `driver_risk_label`, but the final taxonomy remains a placeholder until the real dataset ontology is released. | medium | inspect label taxonomy and judging terminology | mobile output, reporting |
| OR-003 | orchestration identifiers | Real session IDs and network request references will likely follow operator-specific formats, so current mock orchestration uses deterministic local placeholder strings only. | high | inspect Number Verification and QoD environment details | orchestration traces, logging |
| EV-001 | scenario fixtures | Pre-dataset scenario fixtures use placeholder `source_ref`, labels, and expected outcomes to exercise the architecture before real data is available. | high | inspect real dataset identifiers and labels, then replace placeholder scenario content | evaluation, traceability |
| EV-002 | placeholder scoring | Current label agreement metrics measure agreement against synthetic expected outputs, not real AI accuracy. | high | replace synthetic expectations with dataset-backed ground truth when available | evaluation, reporting |
| EV-003 | scenario coverage | The current scenario set covers success, verification failure, and QoD denial paths only; additional dataset-driven edge cases are deferred. | medium | expand scenarios after real data and API constraints are known | evaluation, robustness |
| EX-001 | markdown exports | Judge-friendly markdown is generated from the current scenario report JSON contract, so any future report schema change must update the export renderer too. | medium | compare markdown needs against final report and presentation expectations | reporting, presentation |
| API-001 | local http wrapper | The current HTTP server is a local stdlib wrapper for demos and mobile prototyping only, not a production deployment surface. | high | replace with final client/server integration strategy if the competition setup requires it | demo integration, mobile client |
| API-002 | local endpoint payloads | The local API reuses repository JSON contracts directly; final mobile-facing payloads may require reshaping once the real app and backend boundaries are known. | medium | inspect final mobile UX and telecom environment constraints | mobile integration, local API |
| AN-001 | analyzer inputs | The placeholder analyzer currently consumes structured heuristic cues instead of raw media tensors or frames, because the real dataset and model pipeline are not available yet. | high | replace heuristic inputs with real media ingestion once dataset structure is known | analysis boundary, model integration |
| AN-002 | analyzer outputs | The analysis result schema is intended to remain stable even after real models arrive, with future adapters mapping model outputs into this contract. | medium | compare real model outputs and task taxonomy against the current schema | orchestration integration, local API |
| AN-003 | analysis session controls | The analysis session request uses local boolean controls for verification and QoD availability to keep demo runs deterministic until real telecom environments exist. | high | replace local controls with real environment-driven behavior when Number Verification and QoD endpoints are available | demo flow, local API |

## Observed Dataset Reality In The Current Delivery

- root folder contains exactly three MP4 files: `video_1.mp4`, `video_2.mp4`, `video_3.mp4`
- each video has a companion screenshot folder: `snap_from_video_1/`, `snap_from_video_2/`, `snap_from_video_3/`
- each screenshot folder currently contains four PNG still images
- inspected screenshots show a TOGG vehicle in an indoor parking-garage style environment
- the front plate is visually readable in inspected screenshots
- a driver is visually visible in inspected screenshots
- no JSON, CSV, TXT, YAML, README, or obvious label sidecar files were observed under `data/`

## Unknowns That Must Be Resolved Before Real Model Work

- whether annotations/docs will arrive separately from the current media bundle
- exact annotation format
- exact target taxonomy
- whether speed is frame-level, clip-level, or separately supplied metadata
- whether plate text is given or must be inferred only from imagery
- whether TOGG identity is explicit in labels
- whether multiple vehicles appear in one scene and how the target vehicle is identified
- exact Number Verification and QoD API payloads, auth method, and environment constraints

## Adaptation Checklist For The Future AI Agent

1. Read the real dataset tree and write down the actual structure.
2. Create a real manifest JSON in the shape expected by `examples/assumed_dataset_manifest.json`.
3. Run the manifest checker and list all failed assumptions.
4. Update this file first, assumption by assumption.
5. Update the Python contracts only where the real dataset contradicts current assumptions.
6. Use the adapter-slot flow to resolve the real manifest before implementing any concrete parser.
7. Implement a concrete dataset adapter after the assumptions are updated.
8. Keep the QoD policy thresholds configurable; do not bury dataset-specific constants inside model code.

## What Should Change Immediately If Reality Differs

- If the dataset is image-based instead of video-based, rewrite ingestion and batching around images and frame groups.
- If labels are event-level only, move frame-level detection expectations out of the base contracts.
- If plate text is unavailable, treat plate reading as detection/localization plus optional OCR rather than guaranteed recognition.
- If speed labels are absent, move speed estimation into an optional capability instead of a required output.
- If TOGG identity is not directly labeled, redefine the trigger policy around observable critical cues rather than brand identity.

## Recommended Update Style

For each changed assumption, preserve the original ID and replace only the statement, confidence, and impact notes. That makes downstream AI-assisted adaptation easier to trace.
