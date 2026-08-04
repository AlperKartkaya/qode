from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.data import build_adapter_from_manifest_path


class FinalStageFtrAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest_path = ROOT / "data" / "final_stage" / "faz2" / "manifest.json"
        self.ground_truth_path = self.manifest_path.parent / "ground_truth.json"

    def test_real_manifest_exposes_one_sample_two_variants_and_34_events(self) -> None:
        adapter = build_adapter_from_manifest_path(
            self.manifest_path, dataset_root=self.manifest_path.parent
        )
        inventory = adapter.load_inventory()

        self.assertEqual(adapter.adapter_key, "final_stage_ftr")
        self.assertEqual(inventory.sample_count, 1)
        self.assertEqual(len(inventory.samples[0].artifacts), 2)
        self.assertEqual(
            {(item.width, item.height) for item in inventory.samples[0].artifacts},
            {(426, 240), (1920, 1080)},
        )
        self.assertEqual(
            inventory.samples[0].metadata["ground_truth_event_count"], "34"
        )

    def test_canonical_source_inventory_checksums_match(self) -> None:
        inventory_path = ROOT / "docs" / "final_stage" / "source_inventory.json"
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
        for source in payload["sources"]:
            path = ROOT / source["path"]
            self.assertTrue(path.is_file(), source["path"])
            self.assertEqual(self._sha(path), source["sha256"], source["path"])

        self.assertFalse((ROOT / "faz2_gt (1).json").exists())
        self.assertFalse((ROOT / "OpenGateway").exists())

    def test_missing_local_video_fails_loudly(self) -> None:
        with self._fixture() as (root, manifest):
            manifest["media_assets"][0]["availability"] = "local"
            self._write_manifest(root, manifest)
            with self.assertRaisesRegex(ValueError, "video artifact is missing"):
                build_adapter_from_manifest_path(
                    root / "manifest.json", dataset_root=root
                ).load_inventory()

    def test_corrupt_json_fails_loudly(self) -> None:
        with self._fixture() as (root, manifest):
            (root / "ground_truth.json").write_text("{", encoding="utf-8")
            manifest["ground_truth_sha256"] = self._sha(root / "ground_truth.json")
            self._write_manifest(root, manifest)
            with self.assertRaisesRegex(ValueError, "Invalid final-stage FTR ground truth"):
                build_adapter_from_manifest_path(
                    root / "manifest.json", dataset_root=root
                ).load_inventory()

    def test_duplicate_event_fails_loudly(self) -> None:
        with self._fixture() as (root, manifest):
            payload = json.loads((root / "ground_truth.json").read_text())
            payload["tespitler"].append(copy.deepcopy(payload["tespitler"][0]))
            self._write_ground_truth(root, manifest, payload)
            with self.assertRaisesRegex(ValueError, "Duplicate final-stage event"):
                build_adapter_from_manifest_path(
                    root / "manifest.json", dataset_root=root
                ).load_inventory()

    def test_invalid_label_fails_loudly(self) -> None:
        with self._fixture() as (root, manifest):
            payload = json.loads((root / "ground_truth.json").read_text())
            payload["tespitler"][0]["etiket"] = "unknown_label"
            self._write_ground_truth(root, manifest, payload)
            with self.assertRaisesRegex(ValueError, "Unsupported FTR detection label"):
                build_adapter_from_manifest_path(
                    root / "manifest.json", dataset_root=root
                ).load_inventory()

    def test_negative_timestamp_fails_loudly(self) -> None:
        with self._fixture() as (root, manifest):
            payload = json.loads((root / "ground_truth.json").read_text())
            payload["tespitler"][0]["zaman_saniye"] = -0.1
            self._write_ground_truth(root, manifest, payload)
            with self.assertRaisesRegex(ValueError, "non-negative"):
                build_adapter_from_manifest_path(
                    root / "manifest.json", dataset_root=root
                ).load_inventory()

    def test_timestamp_beyond_video_duration_fails_loudly(self) -> None:
        with self._fixture() as (root, manifest):
            payload = json.loads((root / "ground_truth.json").read_text())
            payload["tespitler"][0]["zaman_saniye"] = 114.0
            self._write_ground_truth(root, manifest, payload)
            with self.assertRaisesRegex(ValueError, "exceeds video duration"):
                build_adapter_from_manifest_path(
                    root / "manifest.json", dataset_root=root
                ).load_inventory()

    def _fixture(self):
        case = self

        class Fixture:
            def __enter__(self):
                self.temporary = tempfile.TemporaryDirectory()
                root = Path(self.temporary.name)
                manifest = json.loads(case.manifest_path.read_text(encoding="utf-8"))
                (root / "ground_truth.json").write_bytes(case.ground_truth_path.read_bytes())
                case._write_manifest(root, manifest)
                return root, manifest

            def __exit__(self, *args):
                self.temporary.cleanup()

        return Fixture()

    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _write_ground_truth(self, root: Path, manifest: dict, payload: dict) -> None:
        path = root / "ground_truth.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        manifest["ground_truth_sha256"] = self._sha(path)
        manifest["ground_truth_event_count"] = len(payload["tespitler"])
        self._write_manifest(root, manifest)

    @staticmethod
    def _write_manifest(root: Path, manifest: dict) -> None:
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
