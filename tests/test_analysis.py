from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.analysis import (
    AnalysisSessionRequest,
    AnalyzerInput,
    PlaceholderSceneAnalyzer,
    run_analysis_session,
)


class PlaceholderSceneAnalyzerTest(unittest.TestCase):
    def test_placeholder_scene_analyzer_detects_target_vehicle_and_plate(self) -> None:
        analyzer = PlaceholderSceneAnalyzer()
        result = analyzer.analyze(
            AnalyzerInput(
                source_ref="placeholder://analysis/1",
                quality_profile="standard",
                target_vehicle_confidence=0.90,
                plate_visibility_score=0.50,
                driver_risk_score=0.10,
                distance_meters=20.0,
                driver_risk_label="placeholder_none",
            )
        )

        self.assertTrue(result.target_vehicle_detected)
        self.assertTrue(result.plate_candidate_detected)


class AnalysisSessionTest(unittest.TestCase):
    def test_run_analysis_session_produces_successful_workflow(self) -> None:
        request = AnalysisSessionRequest(
            session_id="session-1",
            phone_number="+905551112233",
            device_session_id="device-1",
            requested_profile="standard",
            verification_should_pass=True,
            qod_should_allow_boost=True,
            analyzer_input=AnalyzerInput(
                source_ref="placeholder://analysis/1",
                quality_profile="standard",
                target_vehicle_confidence=0.90,
                plate_visibility_score=0.50,
                driver_risk_score=0.10,
                distance_meters=20.0,
                driver_risk_label="placeholder_none",
            ),
        )

        result = run_analysis_session(request)

        self.assertTrue(result.analysis_result.target_vehicle_detected)
        self.assertEqual(result.workflow_result.status, "SUCCESS")
        self.assertEqual(result.workflow_result.mobile_view.active_profile, "boosted")

    def test_run_analysis_session_can_fail_verification(self) -> None:
        request = AnalysisSessionRequest(
            session_id="session-2",
            phone_number="+905551112234",
            device_session_id="device-2",
            requested_profile="standard",
            verification_should_pass=False,
            qod_should_allow_boost=True,
            analyzer_input=AnalyzerInput(
                source_ref="placeholder://analysis/2",
                quality_profile="standard",
                target_vehicle_confidence=0.90,
                plate_visibility_score=0.50,
                driver_risk_score=0.10,
                distance_meters=20.0,
                driver_risk_label="placeholder_none",
            ),
        )

        result = run_analysis_session(request)

        self.assertEqual(result.workflow_result.status, "FAILED")
        self.assertFalse(result.workflow_result.mobile_view.verification_passed)


if __name__ == "__main__":
    unittest.main()
