#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from smart_road_safety.runtime_assets import check_runtime_assets, load_runtime_asset_manifest, sha256_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Download only frozen runtime assets declared by the shared manifest.")
    parser.add_argument("--manifest", default="config/runtime_assets.json")
    parser.add_argument("--asset-root", default="data/weights")
    args = parser.parse_args()
    root = Path(args.asset_root)
    root.mkdir(parents=True, exist_ok=True)
    manifest = load_runtime_asset_manifest(args.manifest)
    blocked: list[str] = []
    for asset in manifest["assets"]:
        expected = asset.get("sha256")
        url = asset.get("download_url")
        target = root / asset["filename"]
        if target.is_file() and expected and sha256_file(target) == expected:
            print(f"[ready] {asset['id']}: {target}")
            continue
        if not expected or not url:
            blocked.append(f"{asset['id']} (unfrozen or unpublished)")
            continue
        temporary = target.with_suffix(target.suffix + ".download")
        print(f"[download] {asset['id']} <- {url}")
        urllib.request.urlretrieve(url, temporary)
        actual = sha256_file(temporary)
        if actual != expected:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"checksum mismatch for {asset['id']}: {actual}")
        temporary.replace(target)
    report = check_runtime_assets(args.manifest, root, mode="final", inspect_classes=False)
    if blocked:
        print("Final bundle remains blocked: " + ", ".join(blocked), file=sys.stderr)
    print(f"asset_root={root} ready={report.ready}")
    return 0 if report.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
