from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BoundingBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def __post_init__(self) -> None:
        if self.x_min >= self.x_max or self.y_min >= self.y_max:
            raise ValueError(
                "BoundingBox min coordinates must be smaller than max coordinates."
            )


@dataclass(frozen=True)
class DetectionRecord:
    category: str
    label: str
    confidence: float
    bbox: BoundingBox | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Detection confidence must be between 0.0 and 1.0.")


@dataclass(frozen=True)
class FrameAnalysis:
    frame_index: int
    timestamp_ms: int
    quality_profile: str
    detections: tuple[DetectionRecord, ...] = ()

    def __post_init__(self) -> None:
        if self.frame_index < 0:
            raise ValueError("frame_index must be non-negative.")
        if self.timestamp_ms < 0:
            raise ValueError("timestamp_ms must be non-negative.")
