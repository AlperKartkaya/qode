#!/usr/bin/env python3
"""Probe and atomically remux the canonical final-stage HLS variants.

The master URL and desired variants live only in the dataset manifest. Ground
truth is not read by this tool and is never copied into runtime input folders.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HlsVariant:
    name: str
    playlist_url: str
    width: int
    height: int
    bandwidth: int
    codecs: str
    segment_count: int
    duration_seconds: float


def _read_url(url: str, timeout: float = 30.0) -> str:
    request = Request(url, headers={"User-Agent": "qode-final-stage-fetch/1"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def parse_attribute_list(line: str) -> dict[str, str]:
    _, _, raw = line.partition(":")
    pairs = re.findall(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)', raw)
    return {key: value.strip('"') for key, value in pairs}


def parse_master_playlist(master_url: str, content: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    variants: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF:"):
            continue
        if index + 1 >= len(lines) or lines[index + 1].startswith("#"):
            raise ValueError("HLS master has a variant without a playlist URI.")
        attrs = parse_attribute_list(line)
        resolution = attrs.get("RESOLUTION", "")
        try:
            width_text, height_text = resolution.lower().split("x", 1)
            width, height = int(width_text), int(height_text)
            bandwidth = int(attrs["BANDWIDTH"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid HLS variant attributes: {line}") from exc
        variants.append(
            {
                "name": attrs.get("NAME", f"{height}p"),
                "playlist_url": urljoin(master_url, lines[index + 1]),
                "width": width,
                "height": height,
                "bandwidth": bandwidth,
                "codecs": attrs.get("CODECS", ""),
            }
        )
    if not variants:
        raise ValueError("HLS master contains no variants.")
    return variants


def parse_media_duration(content: str) -> tuple[int, float]:
    durations: list[float] = []
    for line in content.splitlines():
        if line.startswith("#EXTINF:"):
            try:
                durations.append(float(line.split(":", 1)[1].split(",", 1)[0]))
            except ValueError as exc:
                raise ValueError(f"Invalid HLS segment duration: {line}") from exc
    if not durations:
        raise ValueError("HLS media playlist contains no segments.")
    return len(durations), sum(durations)


def probe_master(master_url: str) -> tuple[HlsVariant, ...]:
    variants = parse_master_playlist(master_url, _read_url(master_url))
    result: list[HlsVariant] = []
    for item in variants:
        count, duration = parse_media_duration(_read_url(item["playlist_url"]))
        result.append(
            HlsVariant(
                **item,
                segment_count=count,
                duration_seconds=round(duration, 6),
            )
        )
    return tuple(result)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_rate(value: str) -> float:
    numerator, separator, denominator = value.partition("/")
    if not separator:
        return float(numerator)
    if float(denominator) == 0:
        raise ValueError("ffprobe returned a zero FPS denominator.")
    return float(numerator) / float(denominator)


def probe_mp4(path: Path, ffprobe: str) -> dict[str, Any]:
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,codec_name,avg_frame_rate:format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    streams = payload.get("streams", [])
    if not streams:
        raise ValueError(f"ffprobe found no video stream in {path}.")
    stream = streams[0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "codec": str(stream["codec_name"]),
        "fps": round(_parse_rate(str(stream["avg_frame_rate"])), 6),
        "duration_seconds": round(float(payload["format"]["duration"]), 6),
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(path)


def fetch_variants(manifest_path: Path, force: bool = False) -> dict[str, str]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_url = payload.get("source_url")
    if not isinstance(source_url, str) or not source_url:
        raise ValueError("Manifest source_url is required.")
    assets = payload.get("media_assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("Manifest media_assets must be a non-empty list.")

    available = {variant.name: variant for variant in probe_master(source_url)}
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")

    dataset_root = manifest_path.parent
    statuses: dict[str, str] = {}
    downloads: list[tuple[Path, Path, dict[str, Any], HlsVariant]] = []
    partial_paths: list[Path] = []
    try:
        for asset in assets:
            if not isinstance(asset, dict):
                raise ValueError("Each media_assets item must be an object.")
            name = str(asset.get("variant_name", ""))
            if name not in available:
                raise ValueError(f"Requested HLS variant {name!r} is unavailable.")
            variant = available[name]
            expected_shape = (int(asset["width"]), int(asset["height"]))
            if (variant.width, variant.height) != expected_shape:
                raise ValueError(
                    f"HLS resolution changed for {name}: expected "
                    f"{expected_shape}, got {(variant.width, variant.height)}."
                )
            expected_segments = int(asset["segment_count"])
            if variant.segment_count != expected_segments:
                raise ValueError(
                    f"HLS segment count changed for {name}: expected "
                    f"{expected_segments}, got {variant.segment_count}."
                )
            expected_duration = float(asset["duration_seconds"])
            if abs(variant.duration_seconds - expected_duration) > 0.05:
                raise ValueError(
                    f"HLS duration changed for {name}: expected "
                    f"{expected_duration}, got {variant.duration_seconds}."
                )
            target = (dataset_root / str(asset["path"])).resolve()
            if dataset_root.resolve() not in target.parents:
                raise ValueError(f"Media path escapes dataset root: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            expected_sha = asset.get("sha256")
            if target.exists() and not force:
                actual_sha = sha256_file(target)
                if expected_sha == actual_sha:
                    statuses[name] = "cached"
                    continue
                raise ValueError(
                    f"Checksum mismatch for existing {target}; use --force only after review."
                )
            if ffmpeg is None or ffprobe is None:
                raise RuntimeError(
                    "ffmpeg and ffprobe are required for HLS remux; "
                    "install/provide them on PATH."
                )
            temporary = target.with_name(target.name + ".partial.mp4")
            temporary.unlink(missing_ok=True)
            partial_paths.append(temporary)
            subprocess.run(
                [
                    ffmpeg,
                    "-nostdin",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    variant.playlist_url,
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a?",
                    "-c",
                    "copy",
                    "-f",
                    "mp4",
                    str(temporary),
                ],
                check=True,
            )
            metadata = probe_mp4(temporary, ffprobe)
            if (metadata["width"], metadata["height"]) != (
                variant.width,
                variant.height,
            ):
                raise ValueError(f"Unexpected remux resolution for {name}: {metadata}")
            downloads.append((temporary, target, asset, variant))

        for temporary, target, asset, variant in downloads:
            metadata = probe_mp4(temporary, ffprobe)
            digest = sha256_file(temporary)
            temporary.replace(target)
            asset.update(metadata)
            asset["duration_seconds"] = variant.duration_seconds
            asset["segment_count"] = variant.segment_count
            asset["sha256"] = digest
            asset["availability"] = "local"
            statuses[variant.name] = "downloaded"
        _atomic_write_json(manifest_path, payload)
        return statuses
    finally:
        for temporary in partial_paths:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default="data/final_stage/faz2/manifest.json",
        type=Path,
    )
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.probe_only:
        variants = probe_master(str(payload["source_url"]))
        print(json.dumps([asdict(item) for item in variants], indent=2))
        return 0
    statuses = fetch_variants(args.manifest, force=args.force)
    print(json.dumps(statuses, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
