from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from ..manifest import DatasetManifest


@dataclass(frozen=True)
class IngestionPlan:
    adapter_key: str
    dataset_root: str | None
    sample_unit: str
    annotation_format: str
    required_assets: tuple[str, ...]
    expected_splits: tuple[str, ...]
    target_families: tuple[str, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)


class DatasetAdapter(ABC):
    adapter_key = "base"

    def __init__(
        self, manifest: DatasetManifest, dataset_root: str | Path | None = None
    ) -> None:
        self.manifest = manifest
        self.dataset_root = None if dataset_root is None else Path(dataset_root)

    @classmethod
    @abstractmethod
    def supports_manifest(cls, manifest: DatasetManifest) -> bool:
        raise NotImplementedError

    @abstractmethod
    def build_ingestion_plan(self) -> IngestionPlan:
        raise NotImplementedError

    def _split_names(self) -> tuple[str, ...]:
        splits: list[str] = []
        if self.manifest.includes_train_split:
            splits.append("train")
        if self.manifest.includes_validation_split:
            splits.append("validation")
        if self.manifest.includes_test_split:
            splits.append("test")
        return tuple(splits)

    def _dataset_root_value(self) -> str | None:
        return None if self.dataset_root is None else str(self.dataset_root)


class AssumedVideoClipDatasetAdapter(DatasetAdapter):
    adapter_key = "assumed_video_clip"

    @classmethod
    def supports_manifest(cls, manifest: DatasetManifest) -> bool:
        return manifest.sample_unit in {"video_clip", "mixed"} and bool(
            manifest.video_extensions
        )

    def build_ingestion_plan(self) -> IngestionPlan:
        notes = [
            "Treat labels as sidecar annotations until the real parser is implemented.",
            "Keep clip-level and frame-level logic separate because both may exist.",
        ]
        if not self.manifest.includes_validation_split:
            notes.append(
                "Prepare to derive an internal validation split from train data."
            )

        return IngestionPlan(
            adapter_key=self.adapter_key,
            dataset_root=self._dataset_root_value(),
            sample_unit=self.manifest.sample_unit,
            annotation_format=self.manifest.annotation_format,
            required_assets=("video files", "annotation sidecars"),
            expected_splits=self._split_names(),
            target_families=self.manifest.targets,
            notes=tuple(notes),
        )


class AssumedFrameDatasetAdapter(DatasetAdapter):
    adapter_key = "assumed_frame_dataset"

    @classmethod
    def supports_manifest(cls, manifest: DatasetManifest) -> bool:
        return manifest.sample_unit == "frame"

    def build_ingestion_plan(self) -> IngestionPlan:
        return IngestionPlan(
            adapter_key=self.adapter_key,
            dataset_root=self._dataset_root_value(),
            sample_unit=self.manifest.sample_unit,
            annotation_format=self.manifest.annotation_format,
            required_assets=("frame images", "annotation sidecars"),
            expected_splits=self._split_names(),
            target_families=self.manifest.targets,
            notes=(
                "Frame-oriented ingestion contradicts the current primary video assumption.",
                "Revisit batching, temporal logic, and QoD trigger windows before model work.",
            ),
        )


class ManifestAdapterRegistry:
    def __init__(self) -> None:
        self._adapter_types: list[type[DatasetAdapter]] = []

    def register(self, adapter_type: type[DatasetAdapter]) -> None:
        self._adapter_types.append(adapter_type)

    def available_adapter_keys(self) -> tuple[str, ...]:
        return tuple(adapter_type.adapter_key for adapter_type in self._adapter_types)

    def resolve(
        self, manifest: DatasetManifest, dataset_root: str | Path | None = None
    ) -> DatasetAdapter:
        for adapter_type in self._adapter_types:
            if adapter_type.supports_manifest(manifest):
                return adapter_type(manifest=manifest, dataset_root=dataset_root)
        available = ", ".join(self.available_adapter_keys()) or "none"
        raise ValueError(
            "No adapter can handle the manifest. "
            f"sample_unit={manifest.sample_unit}, annotation_format={manifest.annotation_format}, "
            f"available_adapters={available}"
        )


def build_default_registry() -> ManifestAdapterRegistry:
    registry = ManifestAdapterRegistry()
    registry.register(AssumedVideoClipDatasetAdapter)
    registry.register(AssumedFrameDatasetAdapter)
    return registry


def build_adapter_from_manifest(
    manifest: DatasetManifest,
    dataset_root: str | Path | None = None,
    registry: ManifestAdapterRegistry | None = None,
) -> DatasetAdapter:
    active_registry = registry if registry is not None else build_default_registry()
    return active_registry.resolve(manifest=manifest, dataset_root=dataset_root)


def build_adapter_from_manifest_path(
    manifest_path: str | Path,
    dataset_root: str | Path | None = None,
    registry: ManifestAdapterRegistry | None = None,
) -> DatasetAdapter:
    manifest = DatasetManifest.from_path(manifest_path)
    return build_adapter_from_manifest(
        manifest=manifest,
        dataset_root=dataset_root,
        registry=registry,
    )
