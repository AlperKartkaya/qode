"""QoDe FTR competition entry point.

Reads one ``.mp4`` from the input directory, runs the real scene-analysis
pipeline, and writes ``results.json`` in the FTR schema. The command defaults to
Docker paths, with a local ``data``/``out`` fallback for development.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent / "src"))

from smart_road_safety.competition.ftr import (
    DetectionEvent,
    FtrCompetitionResult,
    VehicleInfo,
    write_ftr_result,
)

APP_INPUT_DIR = Path("/app/data/input")
APP_OUTPUT_DIR = Path("/app/data/output")
LOCAL_INPUT_DIR = Path("data")
LOCAL_OUTPUT_DIR = Path("out")

YOLO_WEIGHTS = "yolo11x.pt"
DRIVER_WEIGHTS = "data/weights/driver_classifier.pt"
VEHICLE_TYPE_WEIGHTS = "data/weights/vehicle_type_classifier.pt"
SMOOTHING_WINDOW_SECONDS = 3.0
MIN_EVENT_CONFIDENCE = 0.55


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FTR entry point: read one input video and write results.json."
    )
    parser.add_argument("--input-dir", default=str(APP_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(APP_OUTPUT_DIR))
    args = parser.parse_args()

    input_dir = _resolve_input_dir(Path(args.input_dir))
    output_dir = _resolve_output_dir(Path(args.output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    video_path = _single_video(input_dir)
    print(f"[QoDe] Processing: {video_path}")

    cv2_module = _require_video_runtime()
    engine = _build_scene_analysis_engine()
    inferred_vehicle, events = _analyze_video(video_path, engine, cv2_module)
    vehicle_info = _vehicle_info_for_video(input_dir, inferred_vehicle)

    ftr_result = FtrCompetitionResult(
        video_id=video_path.name,
        arac_bilgisi=vehicle_info,
        tespitler=tuple(events),
    )
    target = write_ftr_result(ftr_result, output_dir / "sonuc.json")
    print(f"results_path={target}")
    print(
        "[QoDe] Vehicle: "
        f"{vehicle_info.tip} / {vehicle_info.renk} / {vehicle_info.plaka} "
        f"(conf={vehicle_info.confidence_score:.2f})"
    )
    print(f"[QoDe] Events: {len(events)} unique detection(s)")
    return 0


def _resolve_input_dir(requested: Path) -> Path:
    if requested.exists():
        return requested
    if requested == APP_INPUT_DIR and LOCAL_INPUT_DIR.exists():
        return LOCAL_INPUT_DIR
    raise FileNotFoundError(f"Input directory does not exist: {requested}")


def _resolve_output_dir(requested: Path) -> Path:
    if requested.exists():
        return requested
    if requested == APP_OUTPUT_DIR:
        return LOCAL_OUTPUT_DIR
    return requested


def _single_video(input_dir: Path) -> Path:
    video_files = sorted(path for path in input_dir.glob("*.mp4") if path.stat().st_size > 0)
    if len(video_files) != 1:
        raise RuntimeError(
            f"Expected exactly one non-empty .mp4 in {input_dir}, found {len(video_files)}."
        )
    return video_files[0]


def _require_video_runtime() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV (cv2) is required to run video inference. Install project "
            "requirements or run inside the Docker image before invoking main.py."
        ) from exc
    return cv2


def _build_scene_analysis_engine() -> Any:
    from smart_road_safety.analysis.model_inference import SceneAnalysisEngine

    return SceneAnalysisEngine(
        yolo_model_name=YOLO_WEIGHTS,
        driver_model_path=DRIVER_WEIGHTS,
        vehicle_type_model_path=VEHICLE_TYPE_WEIGHTS,
    )


def _analyze_video(
    video_path: Path, engine: Any, cv2_module: Any
) -> tuple[VehicleInfo | None, list[DetectionEvent]]:
    cap = cv2_module.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2_module.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2_module.CAP_PROP_FRAME_COUNT))
    duration_seconds = total_frames / fps if fps else 0.0
    print(
        f"[QoDe] FPS={fps:.1f} frames={total_frames} "
        f"duration={duration_seconds:.1f}s"
    )

    frame_step = max(1, int(fps))
    vehicle_types: list[str] = []
    vehicle_colors: list[str] = []
    vehicle_scores: list[float] = []
    plate_votes: dict[str, int] = {}
    raw_events: list[dict[str, Any]] = []

    frame_index = 0
    processed = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_index % frame_step == 0:
                timestamp = frame_index / fps
                analysis = engine.analyze_frame(frame, timestamp)
                processed += 1
                if analysis.get("vehicle_detected"):
                    vehicle_types.append(str(analysis["vehicle_type"]))
                    vehicle_colors.append(str(analysis["vehicle_color"]))
                    vehicle_scores.append(float(analysis["vehicle_confidence"]))
                    plate = analysis.get("plate_text")
                    if isinstance(plate, str) and plate.strip():
                        plate_votes[plate] = plate_votes.get(plate, 0) + 1
                for event in analysis.get("driver_events", []):
                    if float(event.get("confidence_score", 0.0)) >= MIN_EVENT_CONFIDENCE:
                        raw_events.append(dict(event))
            frame_index += 1
    finally:
        cap.release()

    print(f"[QoDe] Processed {processed} frame sample(s).")
    events = _deduplicate_events(raw_events)
    vehicle_info = _build_inferred_vehicle_info(vehicle_types, vehicle_colors, vehicle_scores, plate_votes)
    return vehicle_info, events


def _build_inferred_vehicle_info(
    vehicle_types: list[str],
    vehicle_colors: list[str],
    vehicle_scores: list[float],
    plate_votes: dict[str, int],
) -> VehicleInfo | None:
    if not vehicle_types or not vehicle_colors or not vehicle_scores:
        return None
    plate = max(plate_votes, key=plate_votes.get) if plate_votes else "tespit_edilemedi"
    return VehicleInfo(
        tip=str(_mode(vehicle_types)),
        plaka=plate,
        renk=str(_mode(vehicle_colors)),
        confidence_score=round(sum(vehicle_scores) / len(vehicle_scores), 4),
    )


def _vehicle_info_for_video(input_dir: Path, inferred: VehicleInfo | None) -> VehicleInfo:
    sidecar = input_dir / "vehicle_info.json"
    if sidecar.exists():
        return VehicleInfo.from_dict(_read_json_object(sidecar))
    if inferred is not None:
        return inferred
    raise RuntimeError(
        "Vehicle metadata could not be inferred and no vehicle_info.json sidecar was "
        "provided. Refusing to emit placeholder vehicle type/color/plate values."
    )


def _deduplicate_events(raw_events: list[dict[str, Any]]) -> list[DetectionEvent]:
    deduplicated: list[DetectionEvent] = []
    last_seen: dict[tuple[str, str], float] = {}
    for event in sorted(raw_events, key=lambda value: float(value["zaman_saniye"])):
        key = (str(event["kategori"]), str(event["etiket"]))
        timestamp = float(event["zaman_saniye"])
        previous = last_seen.get(key, -999.0)
        if timestamp - previous < SMOOTHING_WINDOW_SECONDS:
            continue
        deduplicated.append(DetectionEvent.from_dict(event))
        last_seen[key] = timestamp
    return deduplicated


def _mode(items: list[str]) -> str:
    return collections.Counter(items).most_common(1)[0][0]


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
