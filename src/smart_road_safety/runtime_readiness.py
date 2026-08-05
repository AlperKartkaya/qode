from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .competition.ftr import FTR_SCHEMA_VERSION
from .runtime_assets import check_runtime_assets


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    checks: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"ready": self.ready, "checks": self.checks}


def check_runtime_readiness(
    manifest_path: str | Path = "config/runtime_assets.json",
    asset_root: str | Path = "/app/weights",
    output_dir: str | Path = "/app/data/output",
    require_gpu: bool = True,
    warmup: bool = True,
) -> ReadinessReport:
    asset_report = check_runtime_assets(manifest_path, asset_root, mode="final", inspect_classes=True)
    checks: dict[str, Any] = {
        "schema_version": {"ok": FTR_SCHEMA_VERSION == "1", "value": FTR_SCHEMA_VERSION},
        "assets": asset_report.to_dict(),
    }
    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        descriptor, probe = tempfile.mkstemp(prefix=".readiness-", dir=output_path)
        os.close(descriptor)
        Path(probe).unlink()
        checks["output_writable"] = {"ok": True, "path": str(output_path)}
    except Exception as exc:
        checks["output_writable"] = {"ok": False, "error": str(exc)}

    try:
        import torch
        gpu_available = bool(torch.cuda.is_available())
        checks["gpu"] = {
            "ok": gpu_available or not require_gpu,
            "required": require_gpu,
            "available": gpu_available,
            "device": torch.cuda.get_device_name(0) if gpu_available else None,
        }
    except Exception as exc:
        checks["gpu"] = {"ok": not require_gpu, "required": require_gpu, "error": str(exc)}

    if warmup and asset_report.ready:
        try:
            _warmup_models(Path(asset_root))
            checks["model_warmup"] = {"ok": True}
        except Exception as exc:
            checks["model_warmup"] = {"ok": False, "error": str(exc)}
    else:
        checks["model_warmup"] = {
            "ok": not warmup,
            "skipped": not warmup,
            "blocked_by_assets": warmup and not asset_report.ready,
        }
    return ReadinessReport(
        ready=all(bool(value.get("ok", value.get("ready", False))) for value in checks.values()),
        checks=checks,
    )


def _warmup_models(root: Path) -> None:
    import numpy as np
    import torch
    from .analysis.model_inference import SceneAnalysisEngine

    engine = SceneAnalysisEngine(
        yolo_model_name=str(root / "yolo11x.pt"),
        driver_model_path=str(root / "driver_classifier_finetuned.pt"),
        smoker_model_path=str(root / "smoker_classifier_finetuned.pt"),
        vehicle_type_model_path=str(root / "vehicle_type_classifier.pt"),
        vehicle_color_model_path=str(root / "vehicle_color_classifier.pt"),
        teknocan_model_path=str(root / "teknocan_detector.pt"),
        plate_model_path=str(root / "license_plate_detector.pt"),
        cabin_model_path=str(root / "cabin_detector.pt"),
        allow_degraded=False,
    )
    blank = np.zeros((640, 640, 3), dtype=np.uint8)
    for model in (engine.yolo, engine.plate_detector, engine.teknocan_yolo, engine.cabin_yolo):
        model(blank, verbose=False)
    classification_input = torch.zeros((1, 3, 224, 224), device=engine.device)
    with torch.no_grad():
        engine.driver_classifier(classification_input)
        engine.smoker_classifier(classification_input)
        engine.vehicle_type_classifier(classification_input)
        engine.vehicle_color_classifier(classification_input)


def readiness_json(**kwargs: Any) -> str:
    return json.dumps(check_runtime_readiness(**kwargs).to_dict(), indent=2)
