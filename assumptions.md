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
- shared domain contracts
- QoD decision simulation based on spec-derived heuristics

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
| DS-002 | sample unit | The main unit of work will be a video clip or video stream segment, even if some labels are frame-level. | high | inspect annotation granularity and sample identifiers | adapters, evaluation, batching |
| DS-003 | annotation source | Labels will likely be supplied in one or more structured sidecar files such as JSON or CSV rather than embedded in the video files. | medium | inspect annotation files and metadata format | parsers, schema validation |
| DS-004 | targets | The dataset will support at least vehicle presence, plate-related information, speed-related information, in-cabin objects, and driver-behavior/risk signals because these are called out in the spec. | high | compare label ontology against these target groups | task routing, model heads |
| DS-005 | plate labels | Plate information may be full text, partially masked text, or only plate regions. Do not assume OCR-ready text is guaranteed. | medium | inspect whether labels contain strings, boxes, masks, or only binary indicators | OCR pipeline, post-processing |
| DS-006 | speed labels | Speed ground truth will likely use `km/h` or equivalent Turkish road-speed units. | medium | inspect metadata field names and units | normalization, reporting |
| DS-007 | in-cabin labels | In-cabin signals may mix objects and behaviors, for example `phone`, `cigarette`, `fatigue`, `distracted`. Do not assume the final class taxonomy yet. | medium | inspect label names and their hierarchy | classification schema, UI labels |
| DS-008 | annotation granularity | Some targets may be frame-level while others may be clip-level or event-level. The dataset may not use one uniform annotation granularity. | medium | inspect examples from every target family | adapters, metrics, temporal smoothing |
| DS-009 | split strategy | The release may provide only a single offline dataset without a clean train/validation/test split, so internal splitting may be required. | medium | inspect dataset folders and documentation | experimentation workflow |
| DS-010 | TOGG trigger | The competition logic requires detecting a critical situation around the TOGG vehicle, but the exact representation of `TOGG approaching` is unknown and must not be hardcoded until observed in data. | high | inspect whether TOGG is class-labeled, visually unique, or externally identified | trigger policy, detection logic |
| DS-011 | quality modes | There will be at least two meaningful video-quality states in practice: normal quality and boosted quality after QoD. | high | inspect stream setup or final API docs | simulation, mobile flow |
| DS-012 | QoD policy | QoD should be requested only when there is an observable benefit such as approach detection, plate-read need, or driver-risk review. | high | confirm against final API docs and judging guidance | trigger policy |
| DS-013 | Number Verification integration | Real Number Verification behavior will only be testable once Turkcell provides the final environment, so current work should use mocks or interface boundaries only. | high | inspect final environment and auth requirements | mobile/auth integration |
| DS-014 | QoD API integration | Real QoD request and response shapes are unknown for now, so current work should model intent and state transitions rather than final HTTP payloads. | high | inspect official endpoint docs, auth, and request contracts | API client, orchestration |
| DS-015 | evaluation focus | Final evaluation will favor a balance of AI accuracy, selective QoD usage, and overall architecture quality rather than raw model complexity alone. | high | compare against final judging and report guidance | roadmap prioritization |
| DS-016 | privacy and sharing | Dataset and network details provided during the competition should be treated as non-public unless clearly stated otherwise. | high | inspect NDA, sharing rules, or package notices | repo hygiene, deployment |

## Unknowns That Must Be Resolved Before Real Model Work

- exact folder and file structure of the dataset
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
6. Implement a concrete dataset adapter after the assumptions are updated.
7. Keep the QoD policy thresholds configurable; do not bury dataset-specific constants inside model code.

## What Should Change Immediately If Reality Differs

- If the dataset is image-based instead of video-based, rewrite ingestion and batching around images and frame groups.
- If labels are event-level only, move frame-level detection expectations out of the base contracts.
- If plate text is unavailable, treat plate reading as detection/localization plus optional OCR rather than guaranteed recognition.
- If speed labels are absent, move speed estimation into an optional capability instead of a required output.
- If TOGG identity is not directly labeled, redefine the trigger policy around observable critical cues rather than brand identity.

## Recommended Update Style

For each changed assumption, preserve the original ID and replace only the statement, confidence, and impact notes. That makes downstream AI-assisted adaptation easier to trace.
