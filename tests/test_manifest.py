from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.manifest import DatasetManifest, compare_manifest_to_assumptions


class ManifestChecksTest(unittest.TestCase):
    def test_manifest_with_full_ftr_coverage_reports_no_gaps(self) -> None:
        manifest = DatasetManifest.from_dict(
            {
                "sample_unit": "video_clip",
                "video_extensions": [".mp4"],
                "annotation_format": "json",
                "includes_train_split": True,
                "includes_validation_split": False,
                "includes_test_split": True,
                "targets": [
                    "driver_behavior",
                    "vehicle",
                    "plate_text",
                    "in_cabin_object",
                ],
                "has_frame_level_annotations": True,
                "has_clip_level_annotations": True,
                "has_plate_text": True,
                "has_speed_ground_truth": True,
                "has_in_cabin_annotations": True,
                "has_driver_behavior_annotations": True,
                "speed_unit": "km/h",
                "ftr_output_families_covered": [
                    "arac_bilgisi",
                    "sofor_eylemi",
                    "nesneler",
                    "yolcular",
                ],
            }
        )

        gaps = compare_manifest_to_assumptions(manifest)
        self.assertEqual(gaps, [])

    def test_manifest_missing_driver_behavior_target_is_high_severity(self) -> None:
        manifest = DatasetManifest.from_dict(
            {
                "sample_unit": "video_clip",
                "video_extensions": [".mp4"],
                "annotation_format": "json",
                "includes_train_split": True,
                "includes_validation_split": True,
                "includes_test_split": True,
                "targets": ["vehicle", "plate"],
                "has_frame_level_annotations": True,
                "has_clip_level_annotations": False,
                "has_plate_text": True,
                "has_speed_ground_truth": True,
                "has_in_cabin_annotations": False,
                "has_driver_behavior_annotations": False,
                "speed_unit": "km/h",
                "ftr_output_families_covered": [
                    "arac_bilgisi",
                    "sofor_eylemi",
                    "nesneler",
                    "yolcular",
                ],
            }
        )

        gaps = compare_manifest_to_assumptions(manifest)

        self.assertTrue(
            any(
                gap.assumption_id == "DS-004" and gap.severity == "high"
                for gap in gaps
            )
        )

    def test_state_farm_manifest_reports_ftr_support_gaps(self) -> None:
        manifest = DatasetManifest.from_path(
            ROOT / "data" / "datasets" / "state-farm-distracted-driver" / "manifest.json"
        )

        gaps = compare_manifest_to_assumptions(manifest)

        self.assertTrue(
            any(
                gap.assumption_id == "DS-004" and gap.severity == "medium"
                for gap in gaps
            )
        )
        self.assertTrue(any(gap.assumption_id == "DS-005" for gap in gaps))

    def test_telemetry_row_dataset_without_video_extensions_reports_ftr_gaps(self) -> None:
        manifest = DatasetManifest.from_path(
            ROOT / "data" / "datasets" / "DriverSVT-teknofest" / "manifest.json"
        )

        gaps = compare_manifest_to_assumptions(manifest)

        self.assertTrue(any(gap.assumption_id == "DS-004" for gap in gaps))
        self.assertTrue(any(gap.assumption_id == "DS-005" for gap in gaps))
        self.assertEqual(manifest.extra_fields["row_count"], 17561501)


if __name__ == "__main__":
    unittest.main()
