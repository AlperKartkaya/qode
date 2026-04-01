# Smart Road Safety

Pre-dataset foundation for the 2026 TEKNOFEST 5G and AI road safety competition.

Current milestone:
- explicit project assumptions in `assumptions.md`
- a small Python core for domain contracts, dataset-manifest checks, adapter-slot planning, integration contracts, and QoD decision simulation
- a mock orchestration flow for session bootstrap, verification, QoD decision, and mobile-facing output
- a deterministic scenario-to-score harness for traceable pre-dataset evaluation
- a markdown export layer and tiny local HTTP API for future demo clients
- a placeholder analysis boundary that feeds future model outputs into the telecom workflow
- a real media-bundle adapter for the delivered dataset under `data/`
- placeholder workspace boundaries for mobile, API, vision, and simulation work

This repository intentionally avoids locking into real dataset parsing before the dataset is released.

## Workspace

- `assumptions.md`: assumption registry for future adaptation work
- `src/smart_road_safety/`: shared pre-dataset core
- `apps/mobile/`: reserved mobile app boundary
- `services/api/`: reserved API boundary
- `services/vision/`: reserved vision/model boundary
- `simulation/`: reserved scenario and evaluation boundary
- `examples/`: sample inputs that match current assumptions
- `tests/`: unit tests for the current milestone

## Commands

```bash
PYTHONPATH=src python3 -m smart_road_safety.cli print-assumptions
PYTHONPATH=src python3 -m smart_road_safety.cli check-manifest examples/assumed_dataset_manifest.json
PYTHONPATH=src python3 -m smart_road_safety.cli plan-ingestion examples/assumed_dataset_manifest.json --dataset-root data/offline
PYTHONPATH=src python3 -m smart_road_safety.cli check-manifest data/real_dataset_manifest.json
PYTHONPATH=src python3 -m smart_road_safety.cli inspect-dataset data/real_dataset_manifest.json --dataset-root data
PYTHONPATH=src python3 -m smart_road_safety.cli print-default-qod-policy
PYTHONPATH=src python3 -m smart_road_safety.cli simulate-qod examples/qod_scenario.json
PYTHONPATH=src python3 -m smart_road_safety.cli simulate-qod examples/qod_scenario.json --policy-path examples/custom_qod_policy.json
PYTHONPATH=src python3 -m smart_road_safety.cli run-mock-orchestration examples/mock_orchestration_request.json
PYTHONPATH=src python3 -m smart_road_safety.cli run-analysis-session examples/analysis_session_request.json
PYTHONPATH=src python3 -m smart_road_safety.cli run-scenarios examples/scenarios --output-path out/scenario_report.json
PYTHONPATH=src python3 -m smart_road_safety.cli export-scenario-report out/scenario_report.json --output-path out/scenario_report.md
PYTHONPATH=src python3 -m smart_road_safety.cli serve-local-api --host 127.0.0.1 --port 8000
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Why this milestone

The competition spec already fixes the broad system shape:
- offline video-based model development comes first
- live/mobile/API integration comes later
- QoD must be triggered only when needed

What is still unknown is the concrete dataset structure, label taxonomy, annotation granularity, and final API details. This repo therefore codifies assumptions and pre-dataset interfaces first.

The current extension points are:
- dataset manifests resolve into adapter slots before any real parser is implemented
- integration contracts reserve the Number Verification and QoD boundaries without assuming final endpoint payloads
- QoD thresholds live in policy JSON rather than in code constants, so the future dataset or API release can tune behavior without redesigning the module
- the orchestration layer composes the mock gateways and typed results so future real clients can replace the mocks without changing the workflow shape
- the evaluation layer runs deterministic scenarios, emits trace bundles, and computes placeholder metrics that can later swap to real dataset-backed scoring
- the export layer turns scenario reports into judge-friendly markdown without changing the underlying JSON contract
- the local HTTP API exposes orchestration, evaluation, and export flows through a thin stdlib wrapper for future mobile or demo integration
- the analysis boundary provides a stable pre-model contract so future dataset-backed analyzers can feed the existing workflow without redesigning orchestration
- the delivered dataset is now ingested as a real mixed media bundle, even though structured labels are still absent from the provided folder
