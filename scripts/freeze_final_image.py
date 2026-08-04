#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist final image identity and tar SHA256.")
    parser.add_argument("--image", required=True)
    parser.add_argument("--output-dir", default="out/final_stage/freeze")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    inspect = json.loads(subprocess.check_output(["docker", "image", "inspect", args.image]))[0]
    tar_path = output / "qode-final.tar"
    with tar_path.open("wb") as handle:
        subprocess.run(["docker", "image", "save", args.image], check=True, stdout=handle)
    digest = hashlib.sha256()
    with tar_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    evidence = {
        "image": args.image,
        "image_id": inspect["Id"],
        "repo_digests": inspect.get("RepoDigests", []),
        "labels": inspect.get("Config", {}).get("Labels", {}),
        "tar_sha256": digest.hexdigest(),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    }
    (output / "image_identity.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
