# Smart Road Safety

Dataset-backed foundation for the 2026 TEKNOFEST 5G and AI road safety competition.

Current milestone:
- explicit project assumptions in `assumptions.md`
- real dataset manifests for the four primary local datasets under `data/datasets/*/manifest.json`
- a legacy observed-media manifest at `data/real_dataset_manifest.json`
- dataset adapters for State Farm, DMD Distraction, DMD Drowsiness, DriverSVT, and the legacy three-video bundle
- a stable analysis contract that maps real dataset ground truth into orchestration-ready driver-risk results
- mock Number Verification and QoD gateways because real telecom endpoint details/credentials are still unavailable
- deterministic scenario evaluation, markdown export, CLI commands, and a tiny stdlib local HTTP API

## Dataset Reality

Primary local datasets expected under `data/datasets/`:

| Dataset | Root | Sample unit | Label source | Current role |
| --- | --- | --- | --- | --- |
| State Farm Distracted Driver | `data/datasets/state-farm-distracted-driver` | labelled image | `driver_imgs_list.csv` + class folders | distraction classification samples |
| DMD Distraction | `data/datasets/dmd-distraction` | multi-camera video session | OpenLABEL frame actions | distraction/action coverage |
| DMD Drowsiness | `data/datasets/dmd-drowsiness` | multi-camera video session | OpenLABEL frame actions | drowsiness/yawning/eye-state coverage |
| DriverSVT | `data/datasets/DriverSVT-teknofest` | telemetry row | CSV `dangerousstate` | telemetry-backed dangerous-state coverage |

Legacy secondary dataset:
- `data/video_1.mp4`, `data/video_2.mp4`, `data/video_3.mp4`
- companion screenshot folders under `data/snap_from_video_*/`
- clip observations in `data/video_observations.json`

Important boundaries:
- State Farm test images are present but unlabeled, so evaluation uses labelled train samples.
- DriverSVT exposes numeric dataset-native speed telemetry; the local README does not document a physical speed unit.
- Vehicle/plate fields remain in the stable analysis/orchestration contract for legacy compatibility, but primary datasets are driver-behavior focused.
- Real Number Verification and QoD endpoint details are not present, so only those external boundaries remain explicit mocks.

## Workspace

- `assumptions.md`: current assumption and reality registry
- `src/smart_road_safety/`: shared project core
- `src/smart_road_safety/data/`: manifest-backed adapters and real dataset loaders
- `src/smart_road_safety/analysis/`: analysis contracts plus dataset-grounded mapping
- `src/smart_road_safety/orchestration/`: Number Verification/QoD workflow composition
- `src/smart_road_safety/evaluation/`: deterministic scenario evaluation and metrics
- `src/smart_road_safety/export/`: markdown reporting
- `src/smart_road_safety/local_api/`: local demo HTTP API
- `examples/`: runnable requests and scenario definitions
- `tests/`: unit and integration tests for the current milestone

Large dataset payloads remain local-only; `.gitignore` keeps `data/datasets/**` ignored except the small manifest JSON files.

## Commands

```bash
# Assumptions and manifests
PYTHONPATH=src python3 -m smart_road_safety.cli print-assumptions
PYTHONPATH=src python3 -m smart_road_safety.cli check-manifest data/datasets/state-farm-distracted-driver/manifest.json
PYTHONPATH=src python3 -m smart_road_safety.cli check-manifest data/datasets/dmd-distraction/manifest.json
PYTHONPATH=src python3 -m smart_road_safety.cli check-manifest data/datasets/dmd-drowsiness/manifest.json
PYTHONPATH=src python3 -m smart_road_safety.cli check-manifest data/datasets/DriverSVT-teknofest/manifest.json

# Dataset inspection
PYTHONPATH=src python3 -m smart_road_safety.cli inspect-dataset data/datasets/state-farm-distracted-driver/manifest.json --dataset-root data/datasets/state-farm-distracted-driver
PYTHONPATH=src python3 -m smart_road_safety.cli inspect-dataset data/datasets/dmd-distraction/manifest.json --dataset-root data/datasets/dmd-distraction
PYTHONPATH=src python3 -m smart_road_safety.cli inspect-dataset data/datasets/dmd-drowsiness/manifest.json --dataset-root data/datasets/dmd-drowsiness
PYTHONPATH=src python3 -m smart_road_safety.cli inspect-dataset data/datasets/DriverSVT-teknofest/manifest.json --dataset-root data/datasets/DriverSVT-teknofest

# Dataset-backed analysis sessions
PYTHONPATH=src python3 -m smart_road_safety.cli run-analysis-session examples/analysis_session_state_farm.json
PYTHONPATH=src python3 -m smart_road_safety.cli run-analysis-session examples/analysis_session_dmd_distraction.json
PYTHONPATH=src python3 -m smart_road_safety.cli run-analysis-session examples/analysis_session_dmd_drowsiness.json
PYTHONPATH=src python3 -m smart_road_safety.cli run-analysis-session examples/analysis_session_driversvt.json
PYTHONPATH=src python3 -m smart_road_safety.cli run-analysis-session examples/analysis_session_request.json

# Evaluation, export, and local API
PYTHONPATH=src python3 -m smart_road_safety.cli run-scenarios examples/scenarios --output-path out/scenario_report.json
PYTHONPATH=src python3 -m smart_road_safety.cli export-scenario-report out/scenario_report.json --output-path out/scenario_report.md
PYTHONPATH=src python3 -m smart_road_safety.cli serve-local-api --host 127.0.0.1 --port 8000
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Current System Shape

The current pipeline is dataset-backed but model-light: adapters load real samples and labels, then the analysis boundary maps those authoritative labels into the stable `AnalysisResult` contract. Orchestration, QoD decisions, local API responses, scenario reports, and markdown exports all consume that same contract.

This lets the repo demonstrate an end-to-end real-data flow now while preserving replacement points for future trained model inference and real telecom clients.

Current extension points:
- dataset manifests resolve to concrete adapters through `build_adapter_from_manifest_path`
- dataset-specific loaders expose State Farm image labels, DMD OpenLABEL sessions, DriverSVT telemetry rows, and legacy media observations
- QoD thresholds live in policy JSON rather than buried dataset-specific constants
- Number Verification and QoD gateway interfaces are stable; mocks are isolated to the unavailable external telecom services
- deterministic scenarios cover all four primary datasets plus the legacy media bundle
- local API endpoints expose orchestration, dataset inventory, analysis session, evaluation, and export flows

## Current Limitation Boundary

The following are explicitly unavailable and therefore remain mocked or optional:
- real Number Verification API environment
- real QoD API environment
- labelled State Farm test ground truth
- official train/validation/test split metadata for DMD and DriverSVT
- official DriverSVT speed unit documentation
- trained model inference; current real-data analysis maps dataset ground truth into the final contract
