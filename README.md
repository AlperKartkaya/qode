# Smart Road Safety

Dataset-backed foundation for the 2026 TEKNOFEST 5G & AI Smart Road Safety competition.

Current source-of-truth order:

1. `5G_ve_Yapay_Zeka_ile_Akıllı_Yol_Güvenliği_Yarışması_-_FTR_Aşaması_Teslim_D.pdf`
2. `2026_5G_YAPAY_ZEKA_İLE_AKILLI_YOL_GÜVENLİĞİ_YARISMASI_SARTNAMESI_2_PORZ6.pdf`
3. `final_report_template.docx`
4. local/open-source support datasets

Current milestone:

- explicit KTR/FTR assumptions in `assumptions.md`
- real dataset manifests for four support datasets under `data/datasets/*/manifest.json`
- a legacy observed-media manifest at `data/real_dataset_manifest.json`
- dataset adapters for State Farm, DMD Distraction, DMD Drowsiness, DriverSVT, and the legacy three-video bundle
- a stable internal analysis/orchestration contract for QoD decisions
- a separate FTR competition `results.json` contract under `src/smart_road_safety/competition/`
- mock Number Verification and QoD gateways because real Turkcell endpoint details/credentials are still unavailable
- deterministic scenario evaluation, markdown export, CLI commands, and a tiny stdlib local HTTP API

## FTR Output Contract

The FTR source document requires the final inference output at `/app/data/output/results.json`:

```json
{
  "video_id": "video_001.mp4",
  "arac_bilgisi": {
    "tip": "sedan",
    "plaka": "34ABC123",
    "renk": "beyaz",
    "confidence_score": 0.94
  },
  "tespitler": [
    {
      "zaman_saniye": 14.5,
      "kategori": "sofor_eylemi",
      "etiket": "telefonla_konusma",
      "confidence_score": 0.89
    }
  ]
}
```

The repo validates exact keys, allowed labels, confidence ranges, ASCII-safe labels, and Turkish plate regex compatibility. Current support datasets do **not** contain exact vehicle type/color/plate text for all cases, so FTR output generation requires explicit `vehicle_info` until a real model/annotation source provides those fields.

## Dataset Reality

Primary local support datasets expected under `data/datasets/`:

| Dataset | Root | Sample unit | Label source | FTR role |
| --- | --- | --- | --- | --- |
| State Farm Distracted Driver | `data/datasets/state-farm-distracted-driver` | labelled image | `driver_imgs_list.csv` + class folders | phone/drinking driver-action support |
| DMD Distraction | `data/datasets/dmd-distraction` | multi-camera video session | OpenLABEL frame actions | phone/drinking/gaze/reaching driver-action support |
| DMD Drowsiness | `data/datasets/dmd-drowsiness` | multi-camera video session | OpenLABEL frame actions | `esneme`/drowsiness support |
| DriverSVT | `data/datasets/DriverSVT-teknofest` | telemetry row | CSV `dangerousstate` | telemetry/speed/risk support |

Legacy secondary dataset:

- `data/video_1.mp4`, `data/video_2.mp4`, `data/video_3.mp4`
- companion screenshot folders under `data/snap_from_video_*/`
- clip observations in `data/video_observations.json`
- useful for local FTR smoke cases, but it lacks exact type/color/plate text labels

Important boundaries:

- The FTR/şartname target set is broader than the current support datasets.
- Plate OCR, vehicle type/color, `teknocan`, `bilgisayar`, and passenger-seat labels need additional data or curated annotation.
- The şartname mentions real speed, but the current FTR `results.json` schema does not include a speed key; speed remains an internal/reporting objective until the schema changes.
- Real Number Verification and QoD endpoint details are not present, so only those external boundaries remain explicit mocks.

## Workspace

- `assumptions.md`: current assumption and reality registry
- `docs/ktr_implementation_plan.md`: KTR/FTR implementation, model, dataset, and report-filling plan
- `src/smart_road_safety/data/`: manifest-backed adapters and real dataset loaders
- `src/smart_road_safety/analysis/`: internal analysis contracts plus dataset-grounded mapping
- `src/smart_road_safety/competition/`: FTR `results.json` schema, validation, and safe converter
- `src/smart_road_safety/orchestration/`: Number Verification/QoD workflow composition
- `src/smart_road_safety/evaluation/`: deterministic scenario evaluation and metrics
- `src/smart_road_safety/export/`: markdown reporting
- `src/smart_road_safety/local_api/`: local demo HTTP API
- `examples/`: runnable requests and scenario definitions
- `tests/`: unit and integration tests for the current milestone

## Developer Setup & Training Guide

To get started with model training and dataset ingestion on this repository:

1. **Virtual Environment Setup:**
   Create a Python virtual environment and install all dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Download Datasets:**
   Ensure you have configured your `HF_TOKEN` in the `.env` file, then run the downloader script to fetch and extract all competition datasets:
   ```bash
   python3 src/smart_road_safety/training/download_datasets.py
   ```

3. **Generate Synthetic License Plates:**
   Run the synthetic Turkish plate generator to build OCR training samples:
   ```bash
   python3 src/smart_road_safety/training/synthetic_plate_generator.py
   ```

4. **YOLO11 Model Training Template:**
   Use the YOLO training checklist and YAML generator to configure and start your YOLO detection model:
   ```bash
   python3 src/smart_road_safety/training/train_yolo.py
   ```

5. **Evaluate Classifier Performance:**
   Evaluate your trained driver classifier's precision, recall, and F1-score on the windshield-simulated validation set:
   ```bash
   PYTHONPATH=src python3 -m smart_road_safety.training.eval_classifier
   ```

## Commands

`build-ftr-output` and `validate-ftr-output` are the competition-schema commands.
The analysis-session, scenario, export, and orchestration commands remain
support/demo utilities for QoD architecture evidence until the final evaluator
and trained model wrapper are added.

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

# FTR/KTR competition output validation
PYTHONPATH=src python3 -m smart_road_safety.cli build-ftr-output examples/analysis_session_request.json --vehicle-info-path examples/ftr_vehicle_info.json --video-id video_1.mp4 --output-path out/results.json --event-time-seconds 1.5
PYTHONPATH=src python3 -m smart_road_safety.cli validate-ftr-output out/results.json

# Evaluation, export, and local API
PYTHONPATH=src python3 -m smart_road_safety.cli run-scenarios examples/scenarios --output-path out/scenario_report.json
PYTHONPATH=src python3 -m smart_road_safety.cli export-scenario-report out/scenario_report.json --output-path out/scenario_report.md
PYTHONPATH=src python3 -m smart_road_safety.cli serve-local-api --host 127.0.0.1 --port 8000
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Current System Shape

The current pipeline is dataset-backed and FTR-aware, but model-light: adapters load real support samples and labels, the internal analysis boundary maps authoritative labels into orchestration-ready driver-risk results, and the competition layer validates or builds source-of-truth `results.json` output only when all required FTR fields are available.

Current extension points:

- dataset manifests resolve to concrete adapters through `build_adapter_from_manifest_path`
- dataset-specific loaders expose State Farm image labels, DMD OpenLABEL sessions, DriverSVT telemetry rows, and legacy media observations
- competition output validation lives in `smart_road_safety.competition`
- QoD thresholds live in policy JSON rather than buried dataset-specific constants
- Number Verification and QoD gateway interfaces are stable; mocks are isolated to unavailable external telecom services
- deterministic scenarios cover all four support datasets plus the legacy media bundle
- local API endpoints expose orchestration, dataset inventory, analysis session, competition output, evaluation, and export flows

## Current Limitation Boundary

The following are explicitly unavailable and therefore remain mocked, optional, or planned:

- real Number Verification API environment
- real QoD API environment
- labelled State Farm test ground truth
- official train/validation/test split metadata for DMD and DriverSVT
- exact FTR vehicle type/color/plate/object/passenger labels for all local samples
- official DriverSVT speed unit documentation
- trained model inference and measured KTR accuracy/FPS tables
- final Docker submission wrapper and model weights
