from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.manifest import DatasetManifest, compare_manifest_to_assumptions


class ManifestChecksTest(unittest.TestCase):
    def test_manifest_placeholder_reports_expected_low_severity_gaps(self) -> None:
        manifest = DatasetManifest.from_dict(
            {
                "sample_unit": "video_clip",
                "video_extensions": [".mp4"],
                "annotation_format": "json",
                "includes_train_split": True,
                "includes_validation_split": False,
                "includes_test_split": True,
                "targets": [
                    "vehicle",
                    "plate",
                    "speed",
                    "in_cabin_object",
                    "driver_behavior",
                ],
                "has_frame_level_annotations": True,
                "has_clip_level_annotations": True,
                "has_plate_text": False,
                "has_speed_ground_truth": True,
                "has_in_cabin_annotations": True,
                "has_driver_behavior_annotations": True,
                "speed_unit": "km/h",
            }
        )

        gaps = compare_manifest_to_assumptions(manifest)
        gap_ids = {gap.assumption_id for gap in gaps}

        self.assertIn("DS-009", gap_ids)
        self.assertIn("DS-005", gap_ids)
        self.assertNotIn("DS-004", gap_ids)

    def test_manifest_missing_targets_is_high_severity(self) -> None:
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
            }
        )

        gaps = compare_manifest_to_assumptions(manifest)

        self.assertTrue(
            any(
                gap.assumption_id == "DS-004" and gap.severity == "high" for gap in gaps
            )
        )


if __name__ == "__main__":
    unittest.main()
