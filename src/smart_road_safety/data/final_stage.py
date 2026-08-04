from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..competition import read_ftr_result
from ..manifest import DatasetManifest
from .adapters import (
    DatasetAdapter,
    DatasetInventory,
    DatasetMediaArtifact,
    DatasetMediaSample,
    IngestionPlan,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_text(payload: dict[str, Any], key: str, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}.{key} must be a non-empty string.")
    return value.strip()


def _positive_number(payload: dict[str, Any], key: str, context: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{context}.{key} must be a positive number.")
    return float(value)


def _resolve_inside(root: Path, relative_path: str, context: str) -> Path:
    candidate = (root / relative_path).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError(f"{context} must stay inside dataset_root.")
    return candidate


class FinalStageFtrAdapter(DatasetAdapter):
    """Loads the organizer's Faz 2 HLS metadata and exact FTR ground truth.

    Ground truth is exposed as development/evaluation metadata only. The adapter is
    intentionally not used by the runtime inference entry point.
    """

    adapter_key = "final_stage_ftr"

    @classmethod
    def supports_manifest(cls, manifest: DatasetManifest) -> bool:
        return (
            manifest.sample_unit == "video_clip"
            and manifest.annotation_format == "ftr_results_json"
        )

    def build_ingestion_plan(self) -> IngestionPlan:
        return IngestionPlan(
            adapter_key=self.adapter_key,
            dataset_root=self._dataset_root_value(),
            sample_unit=self.manifest.sample_unit,
            annotation_format=self.manifest.annotation_format,
            required_assets=("HLS media variants", "FTR ground_truth.json"),
            expected_splits=self._split_names(),
            target_families=self.manifest.targets,
            notes=(
                "Ground truth is restricted to development calibration/evaluation.",
                "The single Faz 2 clip must not be reported as hidden-final generalization.",
            ),
        )

    def load_inventory(self) -> DatasetInventory:
        if self.dataset_root is None:
            raise ValueError("dataset_root is required for the final-stage FTR adapter.")

        root = self.dataset_root
        fields = self.manifest.extra_fields
        sample_id = _required_text(fields, "sample_id", "manifest")
        duration = _positive_number(fields, "duration_seconds", "manifest")
        ground_truth_rel = _required_text(fields, "ground_truth_path", "manifest")
        ground_truth_path = _resolve_inside(root, ground_truth_rel, "ground_truth_path")
        if not ground_truth_path.is_file():
            raise ValueError(f"Final-stage ground truth is missing: {ground_truth_path}")

        expected_gt_sha = _required_text(fields, "ground_truth_sha256", "manifest")
        actual_gt_sha = _sha256(ground_truth_path)
        if actual_gt_sha != expected_gt_sha:
            raise ValueError(
                "Final-stage ground-truth checksum mismatch: "
                f"expected {expected_gt_sha}, got {actual_gt_sha}."
            )

        try:
            ground_truth = read_ftr_result(ground_truth_path)
        except Exception as exc:
            raise ValueError(
                f"Invalid final-stage FTR ground truth at {ground_truth_path}: {exc}"
            ) from exc

        expected_video_id = _required_text(fields, "video_id", "manifest")
        if ground_truth.video_id != expected_video_id:
            raise ValueError(
                f"ground_truth video_id must be {expected_video_id!r}, "
                f"got {ground_truth.video_id!r}."
            )

        expected_events = fields.get("ground_truth_event_count")
        if not isinstance(expected_events, int) or isinstance(expected_events, bool):
            raise ValueError("manifest.ground_truth_event_count must be an integer.")
        if len(ground_truth.tespitler) != expected_events:
            raise ValueError(
                "Final-stage event count mismatch: "
                f"expected {expected_events}, got {len(ground_truth.tespitler)}."
            )

        event_keys: set[tuple[float, str, str]] = set()
        for event in ground_truth.tespitler:
            key = (event.zaman_saniye, event.kategori, event.etiket)
            if key in event_keys:
                raise ValueError(
                    "Duplicate final-stage event: "
                    f"timestamp={event.zaman_saniye}, category={event.kategori}, "
                    f"label={event.etiket}."
                )
            event_keys.add(key)
            if event.zaman_saniye > duration:
                raise ValueError(
                    f"Event timestamp {event.zaman_saniye} exceeds video duration {duration}."
                )

        assets_payload = fields.get("media_assets")
        if not isinstance(assets_payload, list) or len(assets_payload) != 2:
            raise ValueError("manifest.media_assets must contain exactly two variants.")
        source_url = _required_text(fields, "source_url", "manifest")
        artifacts = tuple(
            self._load_artifact(root, item, duration, source_url, index)
            for index, item in enumerate(assets_payload)
        )
        resolutions = {(item.width, item.height) for item in artifacts}
        if len(resolutions) != len(artifacts):
            raise ValueError("Final-stage media variants must have distinct resolutions.")

        primary = max(artifacts, key=lambda item: item.width * item.height)
        sample = DatasetMediaSample(
            sample_id=sample_id,
            video_path=primary.path,
            screenshot_paths=(),
            metadata={
                "video_id": ground_truth.video_id,
                "ground_truth_path": str(ground_truth_path),
                "ground_truth_sha256": actual_gt_sha,
                "ground_truth_event_count": str(len(ground_truth.tespitler)),
                "usage": "development_calibration_only",
            },
            artifacts=artifacts,
        )
        return DatasetInventory(
            dataset_root=str(root),
            sample_unit=self.manifest.sample_unit,
            sample_count=1,
            samples=(sample,),
            notes=(
                "One organizer Faz 2 clip is represented by two remote/local resolution artifacts.",
                "Ground truth is never an inference input.",
            ),
        )

    @staticmethod
    def _load_artifact(
        root: Path,
        payload: Any,
        expected_duration: float,
        default_source_url: str,
        index: int,
    ) -> DatasetMediaArtifact:
        context = f"media_assets[{index}]"
        if not isinstance(payload, dict):
            raise ValueError(f"{context} must be an object.")
        artifact_id = _required_text(payload, "artifact_id", context)
        relative_path = _required_text(payload, "path", context)
        path = _resolve_inside(root, relative_path, f"{context}.path")
        width = int(_positive_number(payload, "width", context))
        height = int(_positive_number(payload, "height", context))
        duration = _positive_number(payload, "duration_seconds", context)
        if abs(duration - expected_duration) > 0.05:
            raise ValueError(
                f"{context}.duration_seconds must match manifest duration "
                f"{expected_duration}; got {duration}."
            )
        availability = _required_text(payload, "availability", context)
        source_url = str(payload.get("source_url", default_source_url)).strip()
        parsed_url = urlparse(source_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError(f"{context}.source_url must be an HTTP(S) URL.")
        expected_sha = payload.get("sha256")
        if expected_sha is not None and (
            not isinstance(expected_sha, str) or len(expected_sha) != 64
        ):
            raise ValueError(f"{context}.sha256 must be null or a 64-character digest.")
        if availability not in {"remote", "local"}:
            raise ValueError(f"{context}.availability must be 'remote' or 'local'.")
        if availability == "local" and not path.is_file():
            raise ValueError(f"Final-stage video artifact is missing: {path}")
        if path.exists():
            if not path.is_file():
                raise ValueError(f"Final-stage video artifact is not a file: {path}")
            if expected_sha is None:
                raise ValueError(f"{context}.sha256 is required for a downloaded artifact.")
            actual_sha = _sha256(path)
            if actual_sha != expected_sha:
                raise ValueError(
                    f"Final-stage video checksum mismatch for {path}: "
                    f"expected {expected_sha}, got {actual_sha}."
                )

        fps = payload.get("fps")
        codec = payload.get("codec")
        segment_count = payload.get("segment_count")
        if (
            not isinstance(segment_count, int)
            or isinstance(segment_count, bool)
            or segment_count <= 0
        ):
            raise ValueError(f"{context}.segment_count must be a positive integer.")
        return DatasetMediaArtifact(
            artifact_id=artifact_id,
            path=str(path),
            width=width,
            height=height,
            duration_seconds=duration,
            sha256=expected_sha,
            fps=None if fps is None else float(fps),
            codec=None if codec is None else str(codec),
            source_url=source_url,
            segment_count=segment_count,
        )
