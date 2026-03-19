# Smart Road Safety

Pre-dataset foundation for the 2026 TEKNOFEST 5G and AI road safety competition.

Current milestone:
- explicit project assumptions in `assumptions.md`
- a small Python core for domain contracts, dataset-manifest checks, adapter-slot planning, integration contracts, and QoD decision simulation
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
PYTHONPATH=src python3 -m smart_road_safety.cli print-default-qod-policy
PYTHONPATH=src python3 -m smart_road_safety.cli simulate-qod examples/qod_scenario.json
PYTHONPATH=src python3 -m smart_road_safety.cli simulate-qod examples/qod_scenario.json --policy-path examples/custom_qod_policy.json
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
