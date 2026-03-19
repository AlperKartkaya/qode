from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.qod import (
    BOOSTED_PROFILE,
    STANDARD_PROFILE,
    SceneSignal,
    evaluate_qod_need,
)
from smart_road_safety.policy import QodPolicy


class QodPolicyTest(unittest.TestCase):
    def test_qod_requests_boost_when_target_vehicle_is_close(self) -> None:
        signal = SceneSignal(
            togg_candidate_confidence=0.90,
            plate_visibility_score=0.50,
            driver_risk_score=0.10,
            distance_meters=20.0,
            current_profile=STANDARD_PROFILE,
        )

        decision = evaluate_qod_need(signal)

        self.assertTrue(decision.should_activate)
        self.assertEqual(decision.requested_profile, BOOSTED_PROFILE)
        self.assertGreaterEqual(len(decision.reasons), 1)

    def test_qod_stays_put_when_scene_is_not_critical(self) -> None:
        signal = SceneSignal(
            togg_candidate_confidence=0.20,
            plate_visibility_score=0.95,
            driver_risk_score=0.10,
            distance_meters=120.0,
            current_profile=STANDARD_PROFILE,
        )

        decision = evaluate_qod_need(signal)

        self.assertFalse(decision.should_activate)
        self.assertEqual(decision.requested_profile, STANDARD_PROFILE)

    def test_custom_policy_can_block_a_default_boost(self) -> None:
        strict_policy = QodPolicy(
            standard_profile="standard",
            boosted_profile="boosted",
            approach_distance_meters=10.0,
            togg_confidence_threshold=0.95,
            plate_visibility_min=0.10,
            plate_visibility_max=0.20,
            driver_risk_threshold=0.80,
            boosted_duration_seconds=15,
        )
        signal = SceneSignal(
            togg_candidate_confidence=0.90,
            plate_visibility_score=0.50,
            driver_risk_score=0.10,
            distance_meters=20.0,
            current_profile=STANDARD_PROFILE,
        )

        decision = evaluate_qod_need(signal, policy=strict_policy)

        self.assertFalse(decision.should_activate)
        self.assertEqual(decision.requested_profile, STANDARD_PROFILE)


if __name__ == "__main__":
    unittest.main()
