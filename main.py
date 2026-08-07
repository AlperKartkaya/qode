"""Deterministic QoDe FTR competition entry point."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent / "src"))

from smart_road_safety.competition import (
    VehicleInfo,
    build_ftr_result_from_timeline,
    write_ftr_result_atomic,
)
from smart_road_safety.inference import VideoInferenceConfig, run_video_inference
from smart_road_safety.runtime_assets import check_runtime_assets

APP_INPUT_DIR = Path("/app/data/input")
APP_OUTPUT_DIR = Path("/app/data/output")
APP_ASSET_ROOT = Path("/app/weights")
LOCAL_INPUT_DIR = Path("data/input")
LOCAL_OUTPUT_DIR = Path("out")
LOCAL_ASSET_ROOT = Path("data/weights")
MEDIA_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run final FTR video inference.")
    parser.add_argument("--input-dir", default=str(APP_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(APP_OUTPUT_DIR))
    parser.add_argument("--asset-root", default=str(APP_ASSET_ROOT))
    parser.add_argument("--asset-manifest", default="config/runtime_assets.json")
    parser.add_argument("--mode", choices=("final", "development"), default=os.getenv("QODE_RUNTIME_MODE", "final"))
    parser.add_argument("--sample-fps", type=float, default=float(os.getenv("QODE_SAMPLE_FPS", "4")))
    parser.add_argument("--allow-degraded-inference", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    degraded = True

    input_dir = _resolve_input_dir(Path(args.input_dir))
    output_dir = _resolve_output_dir(Path(args.output_dir))
    asset_root = _resolve_asset_root(Path(args.asset_root))
    video_path = _single_video(input_dir, allow_sidecar=args.mode == "development")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").unlink(missing_ok=True)

    report = check_runtime_assets(
        args.asset_manifest,
        asset_root,
        mode=args.mode,
        inspect_classes=args.mode == "final",
    )
    if not report.ready:
        details = "; ".join(f"{issue.asset_id}:{issue.code}" for issue in report.issues)
        raise RuntimeError(f"runtime asset readiness failed: {details}")

    cv2_module = _require_video_runtime()
    engine = _build_scene_analysis_engine(asset_root, allow_degraded=args.allow_degraded_inference)
    capture = cv2_module.VideoCapture(str(video_path))
    inference = run_video_inference(
        capture,
        engine,
        cv2_module,
        VideoInferenceConfig(sample_fps=args.sample_fps),
    )
    vehicle_info = _vehicle_info_for_video(input_dir, inference.vehicle_info, args.mode)
    result = build_ftr_result_from_timeline(video_path.name, vehicle_info, inference.events)
    target = write_ftr_result_atomic(result, output_dir / "results.json")
    print(f"results_path={target}")
    print(f"processed_samples={inference.processed_samples}")
    print(f"event_count={len(result.tespitler)}")
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
    return LOCAL_OUTPUT_DIR if requested == APP_OUTPUT_DIR else requested


def _resolve_asset_root(requested: Path) -> Path:
    if requested.exists():
        return requested
    return LOCAL_ASSET_ROOT if requested == APP_ASSET_ROOT else requested


def _single_video(input_dir: Path, allow_sidecar: bool = False) -> Path:
    entries = sorted(path for path in input_dir.iterdir() if not path.name.startswith("."))
    directories = [path.name for path in entries if path.is_dir()]
    if directories:
        raise RuntimeError("Input directory contains unexpected directories: " + ", ".join(directories))
    files = [path for path in entries if path.is_file()]
    media = [path for path in files if path.suffix.lower() in MEDIA_SUFFIXES]
    unexpected_media = [path.name for path in media if path.suffix.lower() != ".mp4"]
    permitted = {"vehicle_info.json"} if allow_sidecar else set()
    unexpected_files = [path.name for path in files if path not in media and path.name not in permitted]
    mp4s = [path for path in media if path.suffix.lower() == ".mp4" and path.stat().st_size > 0]
    if unexpected_media or unexpected_files:
        raise RuntimeError(
            "Input directory contains unsupported files: "
            + ", ".join(unexpected_media + unexpected_files)
        )
    if len(mp4s) != 1:
        raise RuntimeError(f"Expected exactly one non-empty .mp4 in {input_dir}, found {len(mp4s)}.")
    return mp4s[0]


def _require_video_runtime() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError("OpenCV is required; use the final image or install runtime requirements") from exc
    return cv2


def _build_scene_analysis_engine(asset_root: Path, allow_degraded: bool) -> Any:
    from smart_road_safety.analysis.model_inference import SceneAnalysisEngine

    return SceneAnalysisEngine(
        yolo_model_name=str(asset_root / "yolo11x.pt"),
        driver_model_path=str(asset_root / "driver_classifier_finetuned.pt"),
        smoker_model_path=str(asset_root / "smoker_classifier_finetuned.pt"),
        vehicle_type_model_path=str(asset_root / "vehicle_type_classifier.pt"),
        vehicle_color_model_path=str(asset_root / "vehicle_color_classifier.pt"),
        teknocan_model_path=str(asset_root / "teknocan_detector.pt"),
        plate_model_path=str(asset_root / "license_plate_detector.pt"),
        cabin_model_path=str(asset_root / "cabin_detector.pt"),
        allow_degraded=allow_degraded,
    )


def _vehicle_info_for_video(input_dir: Path, inferred: VehicleInfo | None, mode: str) -> VehicleInfo:
    if mode == "development":
        sidecar = input_dir / "vehicle_info.json"
        if sidecar.exists():
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("vehicle_info.json must contain an object")
            return VehicleInfo.from_dict(payload)
    if inferred is None:
        return VehicleInfo(tip="sedan", plaka="tespit_edilemedi", renk="beyaz", confidence_score=0.0)
    return inferred


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[QoDe] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
