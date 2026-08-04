import tempfile
import unittest
from pathlib import Path

import main


class FinalEntrypointTests(unittest.TestCase):
    def test_exactly_one_mp4_and_no_extra_media(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "video.mp4").write_bytes(b"video")
            self.assertEqual(main._single_video(root), root / "video.mp4")
            (root / "other.mov").write_bytes(b"media")
            with self.assertRaisesRegex(RuntimeError, "unsupported"):
                main._single_video(root)

    def test_final_rejects_sidecar(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "video.mp4").write_bytes(b"video")
            (root / "vehicle_info.json").write_text("{}")
            with self.assertRaisesRegex(RuntimeError, "unsupported"):
                main._single_video(root, allow_sidecar=False)

    def test_final_rejects_nested_input_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "video.mp4").write_bytes(b"video")
            (root / "nested").mkdir()
            with self.assertRaisesRegex(RuntimeError, "directories"):
                main._single_video(root)

    def test_final_rejects_degraded_mode_before_runtime_imports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "video.mp4").write_bytes(b"video")
            with self.assertRaisesRegex(RuntimeError, "prohibited"):
                main.main(["--input-dir", str(root), "--output-dir", str(root / "out"), "--allow-degraded-inference"])

    def test_failed_readiness_removes_stale_result(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_dir, output_dir, assets = root / "input", root / "output", root / "assets"
            input_dir.mkdir(); output_dir.mkdir(); assets.mkdir()
            (input_dir / "video.mp4").write_bytes(b"video")
            stale = output_dir / "results.json"
            stale.write_text("stale", encoding="utf-8")
            manifest = Path(__file__).resolve().parents[1] / "config/runtime_assets.json"
            with self.assertRaisesRegex(RuntimeError, "asset readiness failed"):
                main.main([
                    "--input-dir", str(input_dir), "--output-dir", str(output_dir),
                    "--asset-root", str(assets), "--asset-manifest", str(manifest),
                ])
            self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
