from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.integration import (
    MobileSessionBootstrapRequest,
    QodActivationRequest,
    build_qod_activation_request,
)
from smart_road_safety.policy import load_default_qod_policy
from smart_road_safety.qod import SceneSignal, evaluate_qod_need


class IntegrationContractsTest(unittest.TestCase):
    def test_mobile_session_bootstrap_request_validates_required_fields(self) -> None:
        request = MobileSessionBootstrapRequest(
            phone_number="+905551112233",
            device_session_id="device-1",
            requested_profile="standard",
        )

        self.assertEqual(request.phone_number, "+905551112233")
        self.assertEqual(request.requested_profile, "standard")

    def test_qod_activation_request_rejects_invalid_duration(self) -> None:
        with self.assertRaises(ValueError):
            QodActivationRequest(
                session_id="session-1",
                target_profile="boosted",
                reason="need more detail",
                duration_seconds=0,
            )

    def test_qod_decision_can_be_converted_into_activation_request(self) -> None:
        decision = evaluate_qod_need(
            SceneSignal(
                togg_candidate_confidence=0.90,
                plate_visibility_score=0.50,
                driver_risk_score=0.10,
                distance_meters=20.0,
                current_profile="standard",
            )
        )

        request = build_qod_activation_request(
            session_id="session-1",
            decision=decision,
            policy=load_default_qod_policy(),
        )

        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request.target_profile, "boosted")
        self.assertGreater(request.duration_seconds, 0)


if __name__ == "__main__":
    unittest.main()
