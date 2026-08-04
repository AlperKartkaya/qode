from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.data import (
    DMDDistractionAdapter,
    DriverSVTAdapter,
    StateFarmAdapter,
    build_adapter_from_manifest,
    build_adapter_from_manifest_path,
)
from smart_road_safety.manifest import DatasetManifest


class DatasetAdapterTest(unittest.TestCase):
    def test_video_manifest_resolves_video_adapter(self) -> None:
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

        adapter = build_adapter_from_manifest(manifest, dataset_root="data/offline")
        plan = adapter.build_ingestion_plan()

        self.assertEqual(adapter.adapter_key, "assumed_video_clip")
        self.assertIn("video files", plan.required_assets)
        self.assertEqual(plan.dataset_root, "data/offline")

    def test_frame_manifest_resolves_frame_adapter(self) -> None:
        manifest = DatasetManifest.from_dict(
            {
                "sample_unit": "frame",
                "video_extensions": [],
                "annotation_format": "csv",
                "includes_train_split": True,
                "includes_validation_split": True,
                "includes_test_split": False,
                "targets": [
                    "vehicle",
                    "plate",
                    "speed",
                    "in_cabin_object",
                    "driver_behavior",
                ],
                "has_frame_level_annotations": True,
                "has_clip_level_annotations": False,
                "has_plate_text": True,
                "has_speed_ground_truth": True,
                "has_in_cabin_annotations": True,
                "has_driver_behavior_annotations": True,
                "speed_unit": "km/h",
            }
        )

        adapter = build_adapter_from_manifest(manifest)
        plan = adapter.build_ingestion_plan()

        self.assertEqual(adapter.adapter_key, "assumed_frame_dataset")
        self.assertIn("frame images", plan.required_assets)

    def test_real_media_manifest_loads_dataset_inventory(self) -> None:
        adapter = build_adapter_from_manifest_path(
            manifest_path=ROOT / "data" / "real_dataset_manifest.json",
            dataset_root=ROOT / "data",
        )
        inventory = adapter.load_inventory()

        self.assertEqual(adapter.adapter_key, "observed_media_bundle")
        self.assertEqual(inventory.sample_count, 3)
        self.assertEqual(inventory.get_sample("video_1").sample_id, "video_1")
        self.assertEqual(len(inventory.get_sample("video_1").screenshot_paths), 0)
        self.assertTrue(inventory.get_sample("video_1").video_path.endswith("video_1.mp4"))

    def test_openalpr_manifest_is_explicitly_unsupported(self) -> None:
        adapter = build_adapter_from_manifest_path(
            manifest_path=ROOT
            / "data"
            / "datasets"
            / "openalpr-benchmarks"
            / "manifest.json",
            dataset_root=ROOT / "data" / "datasets" / "openalpr-benchmarks",
        )

        self.assertEqual(adapter.adapter_key, "unsupported_dataset")
        with self.assertRaisesRegex(ValueError, "explicitly unsupported"):
            adapter.load_inventory()

    @unittest.skipUnless(
        (ROOT / "data" / "datasets" / "state-farm-distracted-driver" / "driver_imgs_list.csv").exists(),
        "real State Farm dataset is not present",
    )
    def test_state_farm_manifest_loads_real_labelled_inventory(self) -> None:
        adapter = build_adapter_from_manifest_path(
            manifest_path=ROOT
            / "data"
            / "datasets"
            / "state-farm-distracted-driver"
            / "manifest.json",
            dataset_root=ROOT / "data" / "datasets" / "state-farm-distracted-driver",
        )

        self.assertIsInstance(adapter, StateFarmAdapter)
        inventory = adapter.load_state_farm_inventory()

        self.assertEqual(inventory.train_count, 22424)
        self.assertEqual(inventory.test_count, 79726)
        self.assertEqual(len(inventory.subjects), 26)
        self.assertEqual(
            inventory.get_sample("p002_c1_img_16856").class_name, "texting_right"
        )

    @unittest.skipUnless(
        len(list((ROOT / "data" / "datasets" / "dmd-distraction").rglob("*_rgb_ann_distraction.json"))) > 0,
        "real DMD distraction dataset is not present",
    )
    def test_dmd_manifest_discovers_real_sessions(self) -> None:
        adapter = build_adapter_from_manifest_path(
            manifest_path=ROOT / "data" / "datasets" / "dmd-distraction" / "manifest.json",
            dataset_root=ROOT / "data" / "datasets" / "dmd-distraction",
        )

        self.assertIsInstance(adapter, DMDDistractionAdapter)
        inventory = adapter.load_dmd_inventory()
        session = inventory.get_session("gA_1_s2")

        self.assertEqual(inventory.session_count, 3)
        self.assertEqual(session.frame_count, 13641)
        self.assertIn("driver_actions/texting_left", session.action_types)

    @unittest.skipUnless(
        (ROOT / "data" / "datasets" / "DriverSVT-teknofest" / "DriverSVT.csv").exists(),
        "real DriverSVT dataset is not present",
    )
    def test_driversvt_manifest_loads_real_row(self) -> None:
        adapter = build_adapter_from_manifest_path(
            manifest_path=ROOT / "data" / "datasets" / "DriverSVT-teknofest" / "manifest.json",
            dataset_root=ROOT / "data" / "datasets" / "DriverSVT-teknofest",
        )

        self.assertIsInstance(adapter, DriverSVTAdapter)
        inventory = adapter.load_inventory()
        row = adapter.load_row("row:575631")

        self.assertEqual(inventory.sample_count, 17561501)
        self.assertEqual(row.dangerous_state, "No attention")
        self.assertEqual(row.user_id, "4160")


if __name__ == "__main__":
    unittest.main()
