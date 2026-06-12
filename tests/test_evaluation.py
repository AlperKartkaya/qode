from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.evaluation import (
    ExpectedWorkflowOutcome,
    ScenarioDefinition,
    run_scenario_suite,
)


class EvaluationModelsTest(unittest.TestCase):
    def test_expected_outcome_requires_valid_status(self) -> None:
        with self.assertRaises(ValueError):
            ExpectedWorkflowOutcome(
                status="UNKNOWN",
                qod_requested=True,
                qod_accepted=True,
                active_profile="boosted",
                target_vehicle_detected=True,
                plate_candidate_detected=True,
                driver_risk_label="phone_use_while_driving",
            )

    def test_scenario_definition_from_dict_parses_nested_payloads(self) -> None:
        scenario = ScenarioDefinition.from_dict(
            {
                "scenario_id": "scenario-1",
                "description": "Simple success path.",
                "orchestration_request": {
                    "session_id": "session-1",
                    "phone_number": "+905551112233",
                    "device_session_id": "device-1",
                    "requested_profile": "standard",
                    "scene_signal": {
                        "togg_candidate_confidence": 0.9,
                        "plate_visibility_score": 0.5,
                        "driver_risk_score": 0.1,
                        "distance_meters": 20.0,
                        "current_profile": "standard",
                    },
                    "analysis_summary": {
                        "source_ref": "placeholder://scenario/1",
                        "target_vehicle_detected": True,
                        "plate_candidate_detected": True,
                        "driver_risk_label": "phone_use_while_driving",
                    },
                },
                "expected": {
                    "status": "SUCCESS",
                    "qod_requested": True,
                    "qod_accepted": True,
                    "active_profile": "boosted",
                    "target_vehicle_detected": True,
                    "plate_candidate_detected": True,
                    "driver_risk_label": "phone_use_while_driving",
                },
            }
        )

        self.assertEqual(scenario.scenario_id, "scenario-1")
        self.assertIsNotNone(scenario.orchestration_request)
        assert scenario.orchestration_request is not None
        self.assertEqual(scenario.orchestration_request.session_id, "session-1")


class EvaluationRunnerTest(unittest.TestCase):
    def test_run_scenario_suite_summarizes_directory(self) -> None:
        output_path = ROOT / "out" / "test_scenario_report.json"
        report = run_scenario_suite(
            scenario_path=ROOT / "examples" / "scenarios",
            output_path=output_path,
        )

        self.assertEqual(report.summary.scenario_count, 7)
        self.assertEqual(report.summary.expectation_pass_count, 7)
        self.assertEqual(report.summary.average_behavior_label_agreement_score, 1.0)
        self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
