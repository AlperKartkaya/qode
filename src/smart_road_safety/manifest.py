from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_TARGETS = {
    "vehicle",
    "plate",
    "driver_behavior",
}

ALLOWED_SAMPLE_UNITS = {"video_clip", "frame", "mixed"}


@dataclass(frozen=True)
class DatasetManifest:
    sample_unit: str
    video_extensions: tuple[str, ...]
    annotation_format: str
    includes_train_split: bool
    includes_validation_split: bool
    includes_test_split: bool
    targets: tuple[str, ...]
    has_frame_level_annotations: bool
    has_clip_level_annotations: bool
    has_plate_text: bool
    has_speed_ground_truth: bool
    has_in_cabin_annotations: bool
    has_driver_behavior_annotations: bool
    speed_unit: str | None
    notes: str = ""

    @classmethod
    def from_path(cls, file_path: str | Path) -> "DatasetManifest":
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DatasetManifest":
        required_keys = {
            "sample_unit",
            "video_extensions",
            "annotation_format",
            "includes_train_split",
            "includes_validation_split",
            "includes_test_split",
            "targets",
            "has_frame_level_annotations",
            "has_clip_level_annotations",
            "has_plate_text",
            "has_speed_ground_truth",
            "has_in_cabin_annotations",
            "has_driver_behavior_annotations",
            "speed_unit",
        }
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(f"Manifest is missing required keys: {', '.join(missing)}")

        return cls(
            sample_unit=str(payload["sample_unit"]),
            video_extensions=tuple(str(value) for value in payload["video_extensions"]),
            annotation_format=str(payload["annotation_format"]),
            includes_train_split=bool(payload["includes_train_split"]),
            includes_validation_split=bool(payload["includes_validation_split"]),
            includes_test_split=bool(payload["includes_test_split"]),
            targets=tuple(str(value) for value in payload["targets"]),
            has_frame_level_annotations=bool(payload["has_frame_level_annotations"]),
            has_clip_level_annotations=bool(payload["has_clip_level_annotations"]),
            has_plate_text=bool(payload["has_plate_text"]),
            has_speed_ground_truth=bool(payload["has_speed_ground_truth"]),
            has_in_cabin_annotations=bool(payload["has_in_cabin_annotations"]),
            has_driver_behavior_annotations=bool(
                payload["has_driver_behavior_annotations"]
            ),
            speed_unit=None
            if payload["speed_unit"] is None
            else str(payload["speed_unit"]),
            notes=str(payload.get("notes", "")),
        )


@dataclass(frozen=True)
class AdaptationGap:
    assumption_id: str
    severity: str
    message: str
    action: str


def compare_manifest_to_assumptions(manifest: DatasetManifest) -> list[AdaptationGap]:
    gaps: list[AdaptationGap] = []

    if manifest.sample_unit not in ALLOWED_SAMPLE_UNITS:
        gaps.append(
            AdaptationGap(
                assumption_id="DS-002",
                severity="high",
                message=f"Unexpected sample unit: {manifest.sample_unit}",
                action="Update ingestion and batching logic to the real sample unit.",
            )
        )

    if not manifest.video_extensions:
        gaps.append(
            AdaptationGap(
                assumption_id="DS-001",
                severity="high",
                message="No video extensions were declared.",
                action="Confirm whether the dataset is still video-based or image-based.",
            )
        )

    missing_targets = sorted(REQUIRED_TARGETS - set(manifest.targets))
    if missing_targets:
        gaps.append(
            AdaptationGap(
                assumption_id="DS-004",
                severity="high",
                message=f"Missing expected target families: {', '.join(missing_targets)}",
                action="Revise task scope and output contracts to match the real ontology.",
            )
        )

    if (
        not manifest.has_frame_level_annotations
        and not manifest.has_clip_level_annotations
    ):
        gaps.append(
            AdaptationGap(
                assumption_id="DS-008",
                severity="high",
                message="Neither frame-level nor clip-level annotations are declared.",
                action="Inspect the dataset and redefine the annotation contract.",
            )
        )

    if "speed" in manifest.targets and not manifest.has_speed_ground_truth:
        gaps.append(
            AdaptationGap(
                assumption_id="DS-006",
                severity="medium",
                message="Speed ground truth is unavailable.",
                action="Treat speed estimation as optional or derive it from another source if allowed.",
            )
        )

    if manifest.speed_unit and manifest.speed_unit.lower() not in {
        "km/h",
        "kmh",
        "kph",
    }:
        gaps.append(
            AdaptationGap(
                assumption_id="DS-006",
                severity="medium",
                message=f"Unexpected speed unit: {manifest.speed_unit}",
                action="Normalize all speed handling and reporting to the released unit.",
            )
        )

    if "plate_text" in manifest.targets and not manifest.has_plate_text:
        gaps.append(
            AdaptationGap(
                assumption_id="DS-005",
                severity="low",
                message="Plate text is not directly available.",
                action="Plan for plate localization first and optional OCR second.",
            )
        )

    return gaps
