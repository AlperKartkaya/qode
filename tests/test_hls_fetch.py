from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "fetch_final_stage_hls.py"
SPEC = importlib.util.spec_from_file_location("fetch_final_stage_hls", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
hls = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = hls
SPEC.loader.exec_module(hls)


class HlsFetchTest(unittest.TestCase):
    MASTER = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=9155202,NAME=1080p,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2"
high/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=289282,NAME=240p,RESOLUTION=426x240,CODECS="avc1.424015,mp4a.40.2"
low/index.m3u8
"""

    def test_parses_master_and_media_duration(self) -> None:
        variants = hls.parse_master_playlist("https://example.test/master.m3u8", self.MASTER)
        self.assertEqual(variants[0]["playlist_url"], "https://example.test/high/index.m3u8")
        self.assertEqual((variants[1]["width"], variants[1]["height"]), (426, 240))
        count, duration = hls.parse_media_duration(
            "#EXTM3U\n#EXTINF:2.00, no desc\na.ts\n#EXTINF:1.92,\nb.ts\n"
        )
        self.assertEqual(count, 2)
        self.assertAlmostEqual(duration, 3.92)

    def test_existing_matching_files_are_idempotent_without_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media = root / "media"
            media.mkdir()
            target = media / "clip.mp4"
            target.write_bytes(b"already-remuxed")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            manifest = {
                "source_url": "https://example.test/master.m3u8",
                "media_assets": [
                    {
                        "variant_name": "240p",
                        "path": "media/clip.mp4",
                        "sha256": digest,
                        "width": 426,
                        "height": 240,
                        "segment_count": 56,
                        "duration_seconds": 113.92,
                    }
                ],
            }
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            variant = hls.HlsVariant(
                "240p", "https://example.test/low.m3u8", 426, 240,
                289282, "avc1", 56, 113.92
            )
            with patch.object(hls, "probe_master", return_value=(variant,)):
                self.assertEqual(hls.fetch_variants(path), {"240p": "cached"})
                self.assertEqual(hls.fetch_variants(path), {"240p": "cached"})

    def test_existing_checksum_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "clip.mp4"
            target.write_bytes(b"changed")
            path = root / "manifest.json"
            path.write_text(json.dumps({
                "source_url": "https://example.test/master.m3u8",
                "media_assets": [{
                    "variant_name": "240p", "path": "clip.mp4", "sha256": "0" * 64,
                    "width": 426, "height": 240, "segment_count": 56,
                    "duration_seconds": 113.92
                }],
            }), encoding="utf-8")
            variant = hls.HlsVariant(
                "240p", "https://example.test/low.m3u8", 426, 240,
                289282, "avc1", 56, 113.92
            )
            with patch.object(hls, "probe_master", return_value=(variant,)):
                with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                    hls.fetch_variants(path)


if __name__ == "__main__":
    unittest.main()
