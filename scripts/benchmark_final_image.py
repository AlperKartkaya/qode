#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from smart_road_safety.competition import read_ftr_result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark a frozen final image offline.")
    parser.add_argument("--image", required=True)
    parser.add_argument("--case", action="append", required=True, metavar="NAME=VIDEO")
    parser.add_argument("--output", default="out/final_stage/runtime_benchmark.json")
    args = parser.parse_args()
    records = []
    for case in args.case:
        name, source_text = case.split("=", 1)
        source = Path(source_text).resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        with tempfile.TemporaryDirectory(prefix=f"qode-{name}-") as temp:
            root = Path(temp)
            input_dir, output_dir = root / "input", root / "output"
            input_dir.mkdir(); output_dir.mkdir()
            shutil.copy2(source, input_dir / "video.mp4")
            container_name = f"qode-benchmark-{name}-{int(time.time())}"
            command = [
                "docker", "run", "--platform", "linux/amd64", "--name", container_name,
                "--network", "none", "--gpus", "all",
                "-v", f"{input_dir}:/app/data/input:ro",
                "-v", f"{output_dir}:/app/data/output",
                args.image,
            ]
            started = time.monotonic()
            process = subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            peak_memory_bytes = 0
            peak_gpu_mib = 0
            while process.poll() is None:
                peak_memory_bytes = max(peak_memory_bytes, _container_memory(container_name))
                peak_gpu_mib = max(peak_gpu_mib, _gpu_memory())
                time.sleep(0.5)
            stdout, stderr = process.communicate()
            elapsed = time.monotonic() - started
            result = output_dir / "results.json"
            schema_valid = False
            if process.returncode == 0 and result.is_file():
                try:
                    read_ftr_result(result)
                    schema_valid = True
                except (ValueError, OSError, json.JSONDecodeError):
                    pass
            inspect = subprocess.run(
                ["docker", "container", "inspect", "--size", container_name],
                text=True, capture_output=True,
            )
            peak_disk = None
            if inspect.returncode == 0:
                payload = json.loads(inspect.stdout)[0]
                peak_disk = int(payload.get("SizeRw") or 0)
            subprocess.run(["docker", "container", "rm", "-f", container_name], capture_output=True)
            records.append({
                "case": name,
                "source_sha256": sha256(source),
                "wall_seconds": round(elapsed, 3),
                "exit_code": process.returncode,
                "output_sha256": sha256(result) if result.is_file() else None,
                "schema_valid": schema_valid,
                "stdout": stdout[-4000:],
                "stderr": stderr[-4000:],
                "container_memory_peak_bytes": peak_memory_bytes,
                "gpu_memory_peak_mib": peak_gpu_mib,
                "peak_disk_bytes": peak_disk,
            })
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"image": args.image, "cases": records}, indent=2), encoding="utf-8")
    print(target)
    return 0 if all(record["exit_code"] == 0 and record["schema_valid"] for record in records) else 2


def _container_memory(name: str) -> int:
    completed = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", name],
        text=True, capture_output=True,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return 0
    value = completed.stdout.split("/", 1)[0].strip()
    match = re.fullmatch(r"([0-9.]+)([KMG]i?B)", value)
    if not match:
        return 0
    factors = {"KB": 1000, "KiB": 1024, "MB": 1000**2, "MiB": 1024**2, "GB": 1000**3, "GiB": 1024**3}
    return int(float(match.group(1)) * factors[match.group(2)])


def _gpu_memory() -> int:
    completed = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=used_memory", "--format=csv,noheader,nounits"],
        text=True, capture_output=True,
    )
    if completed.returncode != 0:
        return 0
    values = [int(value.strip()) for value in completed.stdout.splitlines() if value.strip().isdigit()]
    return sum(values)


if __name__ == "__main__":
    raise SystemExit(main())
