from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.integration import (
    MockNumberVerificationGateway,
    MockQualityOnDemandGateway,
)
from smart_road_safety.orchestration import (
    SessionRequest,
    TelecomOrchestrator,
    SceneAnalysisSummary,
)
from smart_road_safety.policy import load_default_qod_policy
from smart_road_safety.qod import SceneSignal


def build_request() -> SessionRequest:
    return SessionRequest(
        session_id="session-1",
        phone_number="+905551112233",
        device_session_id="device-1",
        requested_profile="standard",
        scene_signal=SceneSignal(
            togg_candidate_confidence=0.90,
            plate_visibility_score=0.50,
            driver_risk_score=0.10,
            distance_meters=20.0,
            current_profile="standard",
        ),
        analysis_summary=SceneAnalysisSummary(
            source_ref="placeholder://dataset/clip-001",
            target_vehicle_detected=True,
            plate_candidate_detected=True,
            driver_risk_label="placeholder_none",
        ),
    )


class TelecomOrchestratorTest(unittest.TestCase):
    def test_orchestrator_completes_successfully_when_verification_and_qod_pass(
        self,
    ) -> None:
        request = build_request()
        orchestrator = TelecomOrchestrator(
            number_verification_gateway=MockNumberVerificationGateway(
                verified_numbers=(request.phone_number,)
            ),
            quality_on_demand_gateway=MockQualityOnDemandGateway(),
            policy=load_default_qod_policy(),
        )

        result = orchestrator.run(request)

        self.assertEqual(result.status, "SUCCESS")
        self.assertTrue(result.bootstrap_result.verified)
        self.assertIsNotNone(result.qod_request)
        self.assertIsNotNone(result.qod_result)
        assert result.qod_result is not None
        self.assertTrue(result.qod_result.accepted)
        self.assertEqual(result.mobile_view.active_profile, "boosted")

    def test_orchestrator_stops_when_verification_fails(self) -> None:
        request = build_request()
        orchestrator = TelecomOrchestrator(
            number_verification_gateway=MockNumberVerificationGateway(),
            quality_on_demand_gateway=MockQualityOnDemandGateway(),
            policy=load_default_qod_policy(),
        )

        result = orchestrator.run(request)

        self.assertEqual(result.status, "FAILED")
        self.assertFalse(result.bootstrap_result.verified)
        self.assertIsNone(result.qod_request)
        self.assertIsNone(result.qod_result)
        self.assertFalse(result.mobile_view.verification_passed)

    def test_orchestrator_returns_partial_when_qod_is_denied(self) -> None:
        request = build_request()
        orchestrator = TelecomOrchestrator(
            number_verification_gateway=MockNumberVerificationGateway(
                verified_numbers=(request.phone_number,)
            ),
            quality_on_demand_gateway=MockQualityOnDemandGateway(
                available_profiles=("standard",),
            ),
            policy=load_default_qod_policy(),
        )

        result = orchestrator.run(request)

        self.assertEqual(result.status, "PARTIAL")
        self.assertIsNotNone(result.qod_request)
        self.assertIsNotNone(result.qod_result)
        assert result.qod_result is not None
        self.assertFalse(result.qod_result.accepted)
        self.assertEqual(result.mobile_view.active_profile, "standard")


if __name__ == "__main__":
    unittest.main()
