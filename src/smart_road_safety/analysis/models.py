from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..orchestration import MockSessionResult


def _require_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty.")
    return cleaned


def _require_score(value: float, field_name: str) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
    return value


@dataclass(frozen=True)
class AnalyzerInput:
    source_ref: str
    quality_profile: str
    target_vehicle_confidence: float
    plate_visibility_score: float
    driver_risk_score: float
    distance_meters: float | None
    driver_risk_label: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_ref", _require_text(self.source_ref, "source_ref")
        )
        object.__setattr__(
            self,
            "quality_profile",
            _require_text(self.quality_profile, "quality_profile"),
        )
        object.__setattr__(
            self,
            "target_vehicle_confidence",
            _require_score(self.target_vehicle_confidence, "target_vehicle_confidence"),
        )
        object.__setattr__(
            self,
            "plate_visibility_score",
            _require_score(self.plate_visibility_score, "plate_visibility_score"),
        )
        object.__setattr__(
            self,
            "driver_risk_score",
            _require_score(self.driver_risk_score, "driver_risk_score"),
        )
        object.__setattr__(
            self,
            "driver_risk_label",
            _require_text(self.driver_risk_label, "driver_risk_label"),
        )
        if self.distance_meters is not None and self.distance_meters < 0:
            raise ValueError("distance_meters must be non-negative when provided.")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnalyzerInput":
        required_keys = {
            "source_ref",
            "quality_profile",
            "target_vehicle_confidence",
            "plate_visibility_score",
            "driver_risk_score",
            "distance_meters",
            "driver_risk_label",
        }
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(
                f"Analyzer input is missing required keys: {', '.join(missing)}"
            )

        return cls(
            source_ref=str(payload["source_ref"]),
            quality_profile=str(payload["quality_profile"]),
            target_vehicle_confidence=float(payload["target_vehicle_confidence"]),
            plate_visibility_score=float(payload["plate_visibility_score"]),
            driver_risk_score=float(payload["driver_risk_score"]),
            distance_meters=None
            if payload["distance_meters"] is None
            else float(payload["distance_meters"]),
            driver_risk_label=str(payload["driver_risk_label"]),
            notes=tuple(str(value) for value in payload.get("notes", [])),
        )


@dataclass(frozen=True)
class AnalysisResult:
    source_ref: str
    quality_profile: str
    target_vehicle_detected: bool
    target_vehicle_confidence: float
    plate_candidate_detected: bool
    plate_visibility_score: float
    driver_risk_score: float
    driver_risk_label: str
    distance_meters: float | None
    summary_message: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_ref", _require_text(self.source_ref, "source_ref")
        )
        object.__setattr__(
            self,
            "quality_profile",
            _require_text(self.quality_profile, "quality_profile"),
        )
        object.__setattr__(
            self,
            "target_vehicle_confidence",
            _require_score(self.target_vehicle_confidence, "target_vehicle_confidence"),
        )
        object.__setattr__(
            self,
            "plate_visibility_score",
            _require_score(self.plate_visibility_score, "plate_visibility_score"),
        )
        object.__setattr__(
            self,
            "driver_risk_score",
            _require_score(self.driver_risk_score, "driver_risk_score"),
        )
        object.__setattr__(
            self,
            "driver_risk_label",
            _require_text(self.driver_risk_label, "driver_risk_label"),
        )
        object.__setattr__(
            self,
            "summary_message",
            _require_text(self.summary_message, "summary_message"),
        )
        if self.distance_meters is not None and self.distance_meters < 0:
            raise ValueError("distance_meters must be non-negative when provided.")


class SceneAnalyzer(ABC):
    @abstractmethod
    def analyze(self, analyzer_input: AnalyzerInput) -> AnalysisResult:
        raise NotImplementedError


@dataclass(frozen=True)
class DatasetSelection:
    dataset_root: str
    manifest_path: str
    sample_id: str
    observations_path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "dataset_root", _require_text(self.dataset_root, "dataset_root")
        )
        object.__setattr__(
            self, "manifest_path", _require_text(self.manifest_path, "manifest_path")
        )
        object.__setattr__(
            self, "sample_id", _require_text(self.sample_id, "sample_id")
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DatasetSelection":
        required_keys = {"dataset_root", "manifest_path", "sample_id"}
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(
                f"Dataset selection is missing required keys: {', '.join(missing)}"
            )

        return cls(
            dataset_root=str(payload["dataset_root"]),
            manifest_path=str(payload["manifest_path"]),
            sample_id=str(payload["sample_id"]),
            observations_path=None
            if payload.get("observations_path") is None
            else str(payload["observations_path"]),
        )


@dataclass(frozen=True)
class AnalysisSessionRequest:
    session_id: str
    phone_number: str
    device_session_id: str
    requested_profile: str
    analyzer_input: AnalyzerInput | None = None
    dataset_selection: DatasetSelection | None = None
    verification_should_pass: bool = True
    qod_should_allow_boost: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "session_id", _require_text(self.session_id, "session_id")
        )
        object.__setattr__(
            self, "phone_number", _require_text(self.phone_number, "phone_number")
        )
        object.__setattr__(
            self,
            "device_session_id",
            _require_text(self.device_session_id, "device_session_id"),
        )
        object.__setattr__(
            self,
            "requested_profile",
            _require_text(self.requested_profile, "requested_profile"),
        )
        if self.analyzer_input is None and self.dataset_selection is None:
            raise ValueError(
                "AnalysisSessionRequest requires analyzer_input or dataset_selection."
            )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnalysisSessionRequest":
        required_keys = {
            "session_id",
            "phone_number",
            "device_session_id",
            "requested_profile",
        }
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(
                f"Analysis session request is missing required keys: {', '.join(missing)}"
            )

        return cls(
            session_id=str(payload["session_id"]),
            phone_number=str(payload["phone_number"]),
            device_session_id=str(payload["device_session_id"]),
            requested_profile=str(payload["requested_profile"]),
            analyzer_input=None
            if payload.get("analyzer_input") is None
            else AnalyzerInput.from_dict(payload["analyzer_input"]),
            dataset_selection=None
            if payload.get("dataset_selection") is None
            else DatasetSelection.from_dict(payload["dataset_selection"]),
            verification_should_pass=bool(
                payload.get("verification_should_pass", True)
            ),
            qod_should_allow_boost=bool(payload.get("qod_should_allow_boost", True)),
        )

    @classmethod
    def from_path(cls, file_path: str | Path) -> "AnalysisSessionRequest":
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)


@dataclass(frozen=True)
class AnalysisSessionResult:
    analysis_result: AnalysisResult
    workflow_result: MockSessionResult
