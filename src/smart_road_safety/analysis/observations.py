from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
class ObservedEvent:
    label: str
    severity: str
    evidence: tuple[str, ...]
    confidence: float
    source: str
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "label", _require_text(self.label, "label"))
        object.__setattr__(self, "severity", _require_text(self.severity, "severity"))
        object.__setattr__(self, "source", _require_text(self.source, "source"))
        object.__setattr__(self, "summary", _require_text(self.summary, "summary"))
        object.__setattr__(
            self, "confidence", _require_score(self.confidence, "confidence")
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ObservedEvent":
        required_keys = {
            "label",
            "severity",
            "evidence",
            "confidence",
            "source",
            "summary",
        }
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(
                f"Observed event is missing required keys: {', '.join(missing)}"
            )

        return cls(
            label=str(payload["label"]),
            severity=str(payload["severity"]),
            evidence=tuple(str(value) for value in payload["evidence"]),
            confidence=float(payload["confidence"]),
            source=str(payload["source"]),
            summary=str(payload["summary"]),
        )


@dataclass(frozen=True)
class VideoObservation:
    sample_id: str
    vehicle_present: bool
    target_vehicle_present: bool
    plate_visible: bool
    plate_visibility_score: float
    in_cabin_objects: tuple[str, ...]
    driver_events: tuple[ObservedEvent, ...]
    risk_label: str
    risk_score: float
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "sample_id", _require_text(self.sample_id, "sample_id")
        )
        object.__setattr__(
            self, "risk_label", _require_text(self.risk_label, "risk_label")
        )
        object.__setattr__(self, "summary", _require_text(self.summary, "summary"))
        object.__setattr__(
            self,
            "plate_visibility_score",
            _require_score(self.plate_visibility_score, "plate_visibility_score"),
        )
        object.__setattr__(
            self, "risk_score", _require_score(self.risk_score, "risk_score")
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VideoObservation":
        required_keys = {
            "sample_id",
            "vehicle_present",
            "target_vehicle_present",
            "plate_visible",
            "plate_visibility_score",
            "in_cabin_objects",
            "driver_events",
            "risk_label",
            "risk_score",
            "summary",
        }
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(
                f"Video observation is missing required keys: {', '.join(missing)}"
            )

        return cls(
            sample_id=str(payload["sample_id"]),
            vehicle_present=bool(payload["vehicle_present"]),
            target_vehicle_present=bool(payload["target_vehicle_present"]),
            plate_visible=bool(payload["plate_visible"]),
            plate_visibility_score=float(payload["plate_visibility_score"]),
            in_cabin_objects=tuple(str(value) for value in payload["in_cabin_objects"]),
            driver_events=tuple(
                ObservedEvent.from_dict(value) for value in payload["driver_events"]
            ),
            risk_label=str(payload["risk_label"]),
            risk_score=float(payload["risk_score"]),
            summary=str(payload["summary"]),
        )


@dataclass(frozen=True)
class ObservationRegistry:
    samples: tuple[VideoObservation, ...]

    def get_sample(self, sample_id: str) -> VideoObservation:
        for sample in self.samples:
            if sample.sample_id == sample_id:
                return sample
        raise ValueError(f"Unknown observation sample_id: {sample_id}")

    @classmethod
    def from_path(cls, file_path: str | Path) -> "ObservationRegistry":
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        return cls(
            samples=tuple(
                VideoObservation.from_dict(value) for value in payload["samples"]
            )
        )
