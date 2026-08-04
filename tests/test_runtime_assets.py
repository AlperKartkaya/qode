import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from smart_road_safety.runtime_assets import check_runtime_assets


class RuntimeAssetTests(unittest.TestCase):
    def _manifest(self, root: Path, sha: str | None) -> Path:
        path = root / "manifest.json"
        path.write_text(json.dumps({
            "schema_version": 1,
            "model_bundle_version": "test",
            "assets": [{
                "id": "model", "role": "test", "filename": "model.bin",
                "source": "test", "license": "MIT", "model_version": "1",
                "sha256": sha, "expected_classes": ["label"],
                "class_inspection": "sidecar_json", "availability": "published"
            }]
        }), encoding="utf-8")
        return path

    def test_final_requires_file_and_frozen_checksum(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = check_runtime_assets(self._manifest(root, None), root, "final")
            self.assertFalse(report.ready)
            self.assertEqual(report.issues[0].code, "unfrozen_checksum")

    def test_checksum_passes_and_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = b"frozen"
            (root / "model.bin").write_bytes(content)
            expected = hashlib.sha256(content).hexdigest()
            manifest = self._manifest(root, expected)
            self.assertTrue(check_runtime_assets(manifest, root, "final").ready)
            (root / "model.bin").write_bytes(b"changed")
            self.assertEqual(check_runtime_assets(manifest, root, "final").issues[0].code, "checksum_mismatch")

    def test_class_mapping_is_checked_when_requested(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            content = b"frozen"
            model = root / "model.bin"
            model.write_bytes(content)
            model.with_suffix(".bin.json").write_text('{"class_names":["wrong"]}', encoding="utf-8")
            manifest = self._manifest(root, hashlib.sha256(content).hexdigest())
            report = check_runtime_assets(manifest, root, "final", inspect_classes=True)
            self.assertEqual(report.issues[0].code, "class_mapping_mismatch")


if __name__ == "__main__":
    unittest.main()
