from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.competition import (
    DetectionEvent,
    FtrCompetitionResult,
    VehicleInfo,
)
from smart_road_safety.evaluation import (
    evaluate_ftr_files,
    evaluate_ftr_results,
    write_ftr_evaluation_report,
)
from smart_road_safety.export import (
    export_ftr_metrics_markdown,
    render_ftr_metrics_markdown,
)


class FtrMetricsTest(unittest.TestCase):
    def test_ground_truth_against_itself_is_exact(self) -> None:
        path = ROOT / "data" / "final_stage" / "faz2" / "ground_truth.json"
        report = evaluate_ftr_files(path, path, timestamp_tolerance_seconds=1.0)

        self.assertTrue(report.vehicle.type_exact_match)
        self.assertTrue(report.vehicle.color_exact_match)
        self.assertTrue(report.vehicle.plate_normalized_exact_match)
        self.assertTrue(report.vehicle.prediction_plate_regex_valid)
        self.assertEqual(report.vehicle.exact_match_rate, 1.0)
        self.assertEqual(report.events.micro.tp, 34)
        self.assertEqual(report.events.micro.fp, 0)
        self.assertEqual(report.events.micro.fn, 0)
        self.assertEqual(report.events.micro.f1, 1.0)
        self.assertEqual(report.events.macro_f1, 1.0)
        self.assertEqual(report.events.timestamp_mae_seconds, 0.0)
        self.assertEqual(report.prediction_sha256, report.ground_truth_sha256)
        self.assertEqual(
            [item.f1 for item in report.events.sensitivity], [1.0, 1.0, 1.0, 1.0]
        )

    def test_one_prediction_cannot_match_two_nearby_ground_truth_events(self) -> None:
        ground_truth = self._result(
            events=(
                self._event(1.0, "arka_koltuk_2", "yolcular"),
                self._event(1.5, "arka_koltuk_2", "yolcular"),
            )
        )
        prediction = self._result(
            events=(self._event(1.25, "arka_koltuk_2", "yolcular"),)
        )

        report = evaluate_ftr_results(prediction, ground_truth, 0.5)

        self.assertEqual(report.events.micro.tp, 1)
        self.assertEqual(report.events.micro.fp, 0)
        self.assertEqual(report.events.micro.fn, 1)

    def test_matching_maximizes_cardinality_before_minimizing_error(self) -> None:
        ground_truth = self._result(events=(self._event(0.0), self._event(1.0)))
        prediction = self._result(events=(self._event(0.9), self._event(1.1)))

        report = evaluate_ftr_results(prediction, ground_truth, 1.0)

        self.assertEqual(report.events.micro.tp, 2)
        self.assertEqual(report.events.micro.fp, 0)
        self.assertEqual(report.events.micro.fn, 0)

    def test_event_exactly_on_tolerance_boundary_matches(self) -> None:
        ground_truth = self._result(events=(self._event(10.0),))
        prediction = self._result(events=(self._event(11.0),))

        report = evaluate_ftr_results(prediction, ground_truth, 1.0)

        self.assertEqual(report.events.micro.tp, 1)
        self.assertAlmostEqual(report.events.timestamp_mae_seconds or 0.0, 1.0)

    def test_wrong_label_produces_false_positive_and_false_negative(self) -> None:
        ground_truth = self._result(events=(self._event(10.0, "esneme"),))
        prediction = self._result(events=(self._event(10.0, "su_icme"),))

        report = evaluate_ftr_results(prediction, ground_truth, 1.0)

        self.assertEqual(report.events.micro.tp, 0)
        self.assertEqual(report.events.micro.fp, 1)
        self.assertEqual(report.events.micro.fn, 1)
        self.assertEqual(
            report.events.per_label["sofor_eylemi:su_icme"].fp, 1
        )
        self.assertEqual(
            report.events.per_label["sofor_eylemi:esneme"].fn, 1
        )

    def test_invalid_schema_fails_before_writing_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prediction = root / "prediction.json"
            prediction.write_text(json.dumps({"video_id": "video.mp4"}), encoding="utf-8")
            ground_truth = ROOT / "data" / "final_stage" / "faz2" / "ground_truth.json"
            output = root / "metrics.json"

            with self.assertRaisesRegex(ValueError, "missing required keys"):
                report = evaluate_ftr_files(prediction, ground_truth)
                write_ftr_evaluation_report(report, output)
            self.assertFalse(output.exists())

    def test_non_finite_timestamp_and_tolerance_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite and non-negative"):
            self._event(float("nan"))
        with self.assertRaisesRegex(ValueError, "finite and non-negative"):
            evaluate_ftr_results(
                self._result(events=()),
                self._result(events=()),
                float("inf"),
            )

    def test_empty_events_and_empty_families_do_not_divide_by_zero(self) -> None:
        empty = self._result(events=())

        report = evaluate_ftr_results(empty, empty)

        self.assertEqual(report.events.micro.f1, 0.0)
        self.assertEqual(report.events.macro_f1, 0.0)
        self.assertIsNone(report.events.timestamp_mae_seconds)
        self.assertTrue(
            all(metric.f1 == 0.0 for metric in report.events.per_family.values())
        )
        self.assertEqual(report.events.false_positive_events, ())
        self.assertEqual(report.events.false_negative_events, ())

    def test_event_order_does_not_change_metrics_or_matching(self) -> None:
        ground_truth = self._result(
            events=(self._event(1.0), self._event(5.0), self._event(9.0))
        )
        prediction = self._result(
            events=(self._event(9.1), self._event(1.1), self._event(5.1))
        )
        reversed_prediction = replace(
            prediction, tespitler=tuple(reversed(prediction.tespitler))
        )

        first = evaluate_ftr_results(prediction, ground_truth, 0.5)
        second = evaluate_ftr_results(reversed_prediction, ground_truth, 0.5)

        self.assertEqual(first.events, second.events)

    def test_markdown_contains_vehicle_event_sensitivity_and_error_tables(self) -> None:
        ground_truth = self._result(events=(self._event(10.0, "esneme"),))
        prediction = self._result(events=(self._event(10.0, "su_icme"),))
        report = evaluate_ftr_results(prediction, ground_truth, 1.0)

        markdown = render_ftr_metrics_markdown(report.to_dict())

        self.assertIn("## Vehicle Metrics", markdown)
        self.assertIn("## Per-Label Metrics", markdown)
        self.assertIn("## Timestamp Sensitivity", markdown)
        self.assertIn("## False Positives", markdown)
        self.assertIn("## False Negatives", markdown)
        self.assertIn("not an official competition matching rule", markdown)

        with tempfile.TemporaryDirectory() as tmp:
            target = export_ftr_metrics_markdown(
                report.to_dict(), Path(tmp) / "metrics.md"
            )
            self.assertTrue(target.is_file())

    @staticmethod
    def _event(
        time_seconds: float,
        label: str = "esneme",
        category: str = "sofor_eylemi",
    ) -> DetectionEvent:
        return DetectionEvent(
            zaman_saniye=time_seconds,
            kategori=category,
            etiket=label,
            confidence_score=0.9,
        )

    @staticmethod
    def _result(events: tuple[DetectionEvent, ...]) -> FtrCompetitionResult:
        return FtrCompetitionResult(
            video_id="video.mp4",
            arac_bilgisi=VehicleInfo(
                tip="suv",
                plaka="34TC8532",
                renk="siyah",
                confidence_score=0.9,
            ),
            tespitler=events,
        )


if __name__ == "__main__":
    unittest.main()
