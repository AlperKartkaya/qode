import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import main

ROOT = Path(__file__).resolve().parents[1]


class FinalPackagingTests(unittest.TestCase):
    def test_dockerfile_is_fail_closed_final_runtime(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("QODE_RUNTIME_MODE=final", dockerfile)
        self.assertIn("--mode final --inspect-classes", dockerfile)
        self.assertIn('["python3", "/app/main.py", "--mode", "final"', dockerfile)
        self.assertNotIn("Warning: easyocr-tr-en.bundle not found", dockerfile)

    def test_manifest_contains_every_required_final_head_and_pins_urls(self):
        payload = json.loads((ROOT / "config/runtime_assets.json").read_text(encoding="utf-8"))
        by_id = {asset["id"]: asset for asset in payload["assets"]}
        required = {
            "main_detector", "driver_action_classifier", "vehicle_type_classifier",
            "vehicle_color_classifier", "license_plate_detector", "offline_ocr_bundle",
            "teknocan_detector", "smoker_classifier", "cabin_detector",
        }
        self.assertTrue(required.issubset(by_id))
        for asset in payload["assets"]:
            url = asset.get("download_url")
            if url:
                self.assertNotIn("/resolve/main/", url)

    def test_main_passes_manifest_smoker_path_to_engine(self):
        captured = {}

        class FakeEngine:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        module = types.SimpleNamespace(SceneAnalysisEngine=FakeEngine)
        with patch.dict(sys.modules, {"smart_road_safety.analysis.model_inference": module}):
            main._build_scene_analysis_engine(Path("/assets"), allow_degraded=False)
        self.assertEqual(captured["smoker_model_path"], "/assets/smoker_classifier_finetuned.pt")


if __name__ == "__main__":
    unittest.main()
