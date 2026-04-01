# Smart Road Safety

Pre-dataset foundation for the 2026 TEKNOFEST 5G and AI road safety competition.

Current milestone:
- explicit project assumptions in `assumptions.md`
- a real mixed-media dataset inventory under `data/`
- a human-curated observation registry for the three delivered videos
- a Python core for domain contracts, dataset manifest checks, integration contracts, and QoD decision simulation
- a telecom workflow and analysis path that can run from the real media bundle plus authoritative clip observations
- a deterministic scenario-to-score harness for the three real videos
- a markdown export layer and tiny local HTTP API for future demo clients
- a real media-bundle adapter for the delivered dataset under `data/`
- placeholder workspace boundaries for mobile, API, vision, and simulation work

This repository now treats the delivered media-only dataset plus the repository-local observation registry as the authoritative project input.

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
PYTHONPATH=src python3 -m smart_road_safety.cli check-manifest data/real_dataset_manifest.json
PYTHONPATH=src python3 -m smart_road_safety.cli plan-ingestion data/real_dataset_manifest.json --dataset-root data
PYTHONPATH=src python3 -m smart_road_safety.cli inspect-dataset data/real_dataset_manifest.json --dataset-root data
PYTHONPATH=src python3 -m smart_road_safety.cli print-default-qod-policy
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

The delivered dataset is now a fixed media-only bundle of three videos plus screenshots. Because no official structured labels, splits, or telecom API docs will arrive with this delivery, the repository uses `data/video_observations.json` as the authoritative clip-level behavior source instead of waiting for future annotation packages.

The current extension points are:
- dataset manifests resolve into adapter slots and the observed media-bundle adapter loads the real inventory from `data/`
- integration contracts reserve the Number Verification and QoD boundaries while keeping their absent real details explicit
- QoD thresholds live in policy JSON rather than in code constants, so the future dataset or API release can tune behavior without redesigning the module
- the orchestration layer composes the mock gateways and typed results so future real clients can replace the mocks without changing the workflow shape
- the evaluation layer runs deterministic scenarios for the three real videos and computes behavior agreement against the authoritative observation registry
- the export layer turns scenario reports into judge-friendly markdown without changing the underlying JSON contract
- the local HTTP API exposes orchestration, evaluation, and export flows through a thin stdlib wrapper for future mobile or demo integration
- the analysis boundary now joins real media inventory with authoritative clip observations instead of waiting for future structured labels
- the delivered dataset is now ingested as a real mixed media bundle, even though structured labels are still absent from the provided folder
