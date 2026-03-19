from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .policy import QodPolicy, load_default_qod_policy


DEFAULT_QOD_POLICY = load_default_qod_policy()
STANDARD_PROFILE = DEFAULT_QOD_POLICY.standard_profile
BOOSTED_PROFILE = DEFAULT_QOD_POLICY.boosted_profile


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


def evaluate_qod_need(
    signal: SceneSignal, policy: QodPolicy | None = None
) -> QodDecision:
    active_policy = policy if policy is not None else DEFAULT_QOD_POLICY
    reasons: list[str] = []

    if (
        signal.distance_meters is not None
        and signal.distance_meters <= active_policy.approach_distance_meters
        and signal.togg_candidate_confidence >= active_policy.togg_confidence_threshold
    ):
        reasons.append(
            "candidate target vehicle is close enough to justify boosted quality"
        )

    if (
        active_policy.plate_visibility_min
        <= signal.plate_visibility_score
        <= active_policy.plate_visibility_max
    ):
        reasons.append("plate is visible but not yet clear enough for reliable reading")

    if signal.driver_risk_score >= active_policy.driver_risk_threshold:
        reasons.append("driver risk score suggests a higher-detail inspection window")

    should_activate = (
        bool(reasons) and signal.current_profile != active_policy.boosted_profile
    )
    requested_profile = (
        active_policy.boosted_profile if should_activate else signal.current_profile
    )
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
