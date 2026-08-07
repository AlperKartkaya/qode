from __future__ import annotations

import collections
import math
from dataclasses import dataclass
from typing import Any, Mapping

from ..competition.ftr import DetectionEvent, VehicleInfo


@dataclass(frozen=True)
class TemporalPolicy:
    minimum_samples: int
    maximum_gap_seconds: float


@dataclass(frozen=True)
class VideoInferenceConfig:
    sample_fps: float = 4.0
    minimum_event_confidence: float = 0.55

    def __post_init__(self) -> None:
        if not 3.0 <= self.sample_fps <= 5.0:
            raise ValueError("sample_fps must be between 3 and 5")


@dataclass(frozen=True)
class VideoInferenceResult:
    vehicle_info: VehicleInfo | None
    events: tuple[DetectionEvent, ...]
    processed_samples: int
    source_fps: float


_POLICIES: dict[str, TemporalPolicy] = {
    "sofor_eylemi": TemporalPolicy(2, 0.75),
    "nesneler": TemporalPolicy(1, 0.75),
    "yolcular": TemporalPolicy(1, 1.0),
}


class TemporalEventAggregator:
    def __init__(self) -> None:
        self._active: dict[tuple[str, str], dict[str, Any]] = {}
        self._output: list[dict[str, Any]] = []
        self._emitted_keys: set[tuple[str, str]] = set()

    def observe(self, timestamp: float, candidates: list[Mapping[str, Any]]) -> None:
        visible: set[tuple[str, str]] = set()
        for candidate in candidates:
            category = str(candidate["kategori"])
            label = str(candidate["etiket"])
            key = (category, label)
            visible.add(key)
            policy = TemporalPolicy(1, 1.0) if label == "slalom" else _POLICIES[category]
            state = self._active.get(key)
            if state is None or timestamp - state["last"] > policy.maximum_gap_seconds:
                state = {"first": timestamp, "last": timestamp, "count": 0, "max": 0.0, "record": None}
                self._active[key] = state
            state["last"] = timestamp
            state["count"] += 1
            state["max"] = max(state["max"], float(candidate["confidence_score"]))
            
            if state["record"] is None and state["count"] >= policy.minimum_samples:
                if key not in self._emitted_keys:
                    record = {
                        "zaman_saniye": round(float(state["first"]), 3),
                        "kategori": category,
                        "etiket": label,
                        "confidence_score": round(float(state["max"]), 4),
                    }
                    state["record"] = record
                    self._output.append(record)
                    self._emitted_keys.add(key)
            elif state["record"] is not None:
                state["record"]["confidence_score"] = round(float(state["max"]), 4)

        for key, state in list(self._active.items()):
            policy = TemporalPolicy(1, 1.0) if key[1] == "slalom" else _POLICIES[key[0]]
            if key not in visible and timestamp - state["last"] > policy.maximum_gap_seconds:
                del self._active[key]

    def events(self) -> tuple[DetectionEvent, ...]:
        ordered = sorted(
            self._output,
            key=lambda item: (float(item["zaman_saniye"]), str(item["kategori"]), str(item["etiket"])),
        )
        return tuple(DetectionEvent.from_dict(item) for item in ordered)


class SlalomMotionDetector:
    """Detect alternating lateral vehicle motion from normalized track centers."""

    def __init__(self, movement_threshold: float = 0.035) -> None:
        self._threshold = movement_threshold
        self._last_center: float | None = None
        self._direction: int | None = None
        self._reversals: list[float] = []
        self._emitted = False

    def observe(self, timestamp: float, box: list[float] | None, frame_width: float) -> dict[str, Any] | None:
        if box is None or frame_width <= 0:
            return None
        center = ((float(box[0]) + float(box[2])) / 2.0) / frame_width
        if self._last_center is None:
            self._last_center = center
            return None
        delta = center - self._last_center
        self._last_center = center
        if abs(delta) < self._threshold:
            return None
        direction = 1 if delta > 0 else -1
        if self._direction is not None and direction != self._direction:
            self._reversals.append(timestamp)
            self._reversals = [value for value in self._reversals if timestamp - value <= 4.0]
        self._direction = direction
        if len(self._reversals) >= 2 and not self._emitted:
            self._emitted = True
            return {
                "zaman_saniye": self._reversals[0],
                "kategori": "sofor_eylemi",
                "etiket": "slalom",
                "confidence_score": min(0.95, 0.65 + 0.1 * len(self._reversals)),
            }
        return None


def run_video_inference(
    capture: Any,
    engine: Any,
    cv2_module: Any,
    config: VideoInferenceConfig = VideoInferenceConfig(),
) -> VideoInferenceResult:
    if not capture.isOpened():
        raise RuntimeError("video capture is not open")
    source_fps = float(capture.get(cv2_module.CAP_PROP_FPS) or 0.0)
    if not math.isfinite(source_fps) or source_fps <= 0:
        raise RuntimeError("video has no valid FPS metadata")
    interval = 1.0 / config.sample_fps
    next_sample = 0.0
    last_pts = -1.0
    frame_index = 0
    processed = 0
    aggregator = TemporalEventAggregator()
    slalom = SlalomMotionDetector()
    types: list[str] = []
    colors: list[str] = []
    scores: list[float] = []
    plates: collections.Counter[str] = collections.Counter()
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            pts_ms = float(capture.get(cv2_module.CAP_PROP_POS_MSEC) or 0.0)
            timestamp = pts_ms / 1000.0 if pts_ms > 0 else frame_index / source_fps
            if timestamp + 1e-9 < last_pts:
                raise RuntimeError("non-monotonic video PTS")
            last_pts = timestamp
            if timestamp + 1e-9 < next_sample:
                frame_index += 1
                continue
            while next_sample <= timestamp + 1e-9:
                next_sample += interval
            analysis = engine.analyze_frame(frame, timestamp)
            processed += 1
            if analysis.get("vehicle_detected"):
                types.append(str(analysis["vehicle_type"]))
                colors.append(str(analysis["vehicle_color"]))
                scores.append(float(analysis["vehicle_confidence"]))
                plate = analysis.get("plate_text")
                if isinstance(plate, str) and plate:
                    plates[plate] += 1
            candidates = [
                event for event in analysis.get("driver_events", [])
                if float(event.get("confidence_score", 0.0)) >= config.minimum_event_confidence
                and event.get("etiket") != "slalom"
            ]
            frame_width = float(frame.shape[1]) if hasattr(frame, "shape") else 0.0
            slalom_event = slalom.observe(timestamp, analysis.get("vehicle_box"), frame_width)
            if slalom_event is not None:
                candidates.append(slalom_event)
            aggregator.observe(timestamp, candidates)
            frame_index += 1
    finally:
        capture.release()

    vehicle = _build_vehicle_info(types, colors, scores, plates)
    return VideoInferenceResult(vehicle, aggregator.events(), processed, source_fps)


def _build_vehicle_info(
    types: list[str], colors: list[str], scores: list[float], plates: collections.Counter[str]
) -> VehicleInfo | None:
    if not types or not colors or not scores:
        return None
    return VehicleInfo(
        tip=collections.Counter(types).most_common(1)[0][0],
        renk=collections.Counter(colors).most_common(1)[0][0],
        plaka=plates.most_common(1)[0][0] if plates else "tespit_edilemedi",
        confidence_score=round(sum(scores) / len(scores), 4),
    )
