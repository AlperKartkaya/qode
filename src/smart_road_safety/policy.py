from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class QodPolicy:
    standard_profile: str
    boosted_profile: str
    approach_distance_meters: float
    togg_confidence_threshold: float
    plate_visibility_min: float
    plate_visibility_max: float
    driver_risk_threshold: float
    boosted_duration_seconds: int

    def __post_init__(self) -> None:
        if not self.standard_profile.strip():
            raise ValueError("standard_profile must not be empty.")
        if not self.boosted_profile.strip():
            raise ValueError("boosted_profile must not be empty.")
        if self.approach_distance_meters <= 0:
            raise ValueError("approach_distance_meters must be positive.")
        if not 0.0 <= self.togg_confidence_threshold <= 1.0:
            raise ValueError("togg_confidence_threshold must be between 0.0 and 1.0.")
        if not 0.0 <= self.plate_visibility_min <= 1.0:
            raise ValueError("plate_visibility_min must be between 0.0 and 1.0.")
        if not 0.0 <= self.plate_visibility_max <= 1.0:
            raise ValueError("plate_visibility_max must be between 0.0 and 1.0.")
        if self.plate_visibility_min > self.plate_visibility_max:
            raise ValueError(
                "plate_visibility_min must not be greater than plate_visibility_max."
            )
        if not 0.0 <= self.driver_risk_threshold <= 1.0:
            raise ValueError("driver_risk_threshold must be between 0.0 and 1.0.")
        if self.boosted_duration_seconds <= 0:
            raise ValueError("boosted_duration_seconds must be positive.")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "QodPolicy":
        required_keys = {
            "standard_profile",
            "boosted_profile",
            "approach_distance_meters",
            "togg_confidence_threshold",
            "plate_visibility_min",
            "plate_visibility_max",
            "driver_risk_threshold",
            "boosted_duration_seconds",
        }
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(f"Policy is missing required keys: {', '.join(missing)}")

        return cls(
            standard_profile=str(payload["standard_profile"]),
            boosted_profile=str(payload["boosted_profile"]),
            approach_distance_meters=float(payload["approach_distance_meters"]),
            togg_confidence_threshold=float(payload["togg_confidence_threshold"]),
            plate_visibility_min=float(payload["plate_visibility_min"]),
            plate_visibility_max=float(payload["plate_visibility_max"]),
            driver_risk_threshold=float(payload["driver_risk_threshold"]),
            boosted_duration_seconds=int(payload["boosted_duration_seconds"]),
        )

    @classmethod
    def from_path(cls, file_path: str | Path) -> "QodPolicy":
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_default_qod_policy() -> QodPolicy:
    raw_policy = (
        files("smart_road_safety.policies")
        .joinpath("default_qod_policy.json")
        .read_text(encoding="utf-8")
    )
    return QodPolicy.from_dict(json.loads(raw_policy))
