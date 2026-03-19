from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


STANDARD_PROFILE = "standard"
BOOSTED_PROFILE = "boosted"
APPROACH_DISTANCE_METERS = 40.0
TOGG_CONFIDENCE_THRESHOLD = 0.70
PLATE_VISIBILITY_WINDOW = (0.25, 0.80)
DRIVER_RISK_THRESHOLD = 0.65


@dataclass(frozen=True)
class SceneSignal:
    togg_candidate_confidence: float
    plate_visibility_score: float
    driver_risk_score: float
    distance_meters: float | None
    current_profile: str = STANDARD_PROFILE

    @classmethod
    def from_path(cls, file_path: str | Path) -> "SceneSignal":
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        return cls(
            togg_candidate_confidence=float(payload["togg_candidate_confidence"]),
            plate_visibility_score=float(payload["plate_visibility_score"]),
            driver_risk_score=float(payload["driver_risk_score"]),
            distance_meters=None
            if payload["distance_meters"] is None
            else float(payload["distance_meters"]),
            current_profile=str(payload.get("current_profile", STANDARD_PROFILE)),
        )


@dataclass(frozen=True)
class QodDecision:
    should_activate: bool
    requested_profile: str
    reasons: tuple[str, ...]
    expected_benefit: str


def evaluate_qod_need(signal: SceneSignal) -> QodDecision:
    reasons: list[str] = []

    if (
        signal.distance_meters is not None
        and signal.distance_meters <= APPROACH_DISTANCE_METERS
        and signal.togg_candidate_confidence >= TOGG_CONFIDENCE_THRESHOLD
    ):
        reasons.append(
            "candidate target vehicle is close enough to justify boosted quality"
        )

    if (
        PLATE_VISIBILITY_WINDOW[0]
        <= signal.plate_visibility_score
        <= PLATE_VISIBILITY_WINDOW[1]
    ):
        reasons.append("plate is visible but not yet clear enough for reliable reading")

    if signal.driver_risk_score >= DRIVER_RISK_THRESHOLD:
        reasons.append("driver risk score suggests a higher-detail inspection window")

    should_activate = bool(reasons) and signal.current_profile != BOOSTED_PROFILE
    requested_profile = BOOSTED_PROFILE if should_activate else signal.current_profile
    expected_benefit = (
        "better detail for plate, in-cabin, or target-vehicle analysis"
        if should_activate
        else "stay on the current profile because there is no strong evidence of benefit"
    )

    return QodDecision(
        should_activate=should_activate,
        requested_profile=requested_profile,
        reasons=tuple(reasons),
        expected_benefit=expected_benefit,
    )
