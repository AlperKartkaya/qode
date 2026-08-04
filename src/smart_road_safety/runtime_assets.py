from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("config/runtime_assets.json")


@dataclass(frozen=True)
class AssetIssue:
    asset_id: str
    code: str
    message: str


@dataclass(frozen=True)
class AssetCheckReport:
    mode: str
    manifest_version: str
    checked_assets: int
    issues: tuple[AssetIssue, ...]

    @property
    def ready(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "manifest_version": self.manifest_version,
            "checked_assets": self.checked_assets,
            "ready": self.ready,
            "issues": [issue.__dict__ for issue in self.issues],
        }


def load_runtime_asset_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("runtime asset manifest schema_version must be 1")
    assets = payload.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("runtime asset manifest must contain assets")
    ids = [asset.get("id") for asset in assets]
    if len(ids) != len(set(ids)):
        raise ValueError("runtime asset ids must be unique")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_runtime_assets(
    manifest_path: str | Path = DEFAULT_MANIFEST,
    asset_root: str | Path = "data/weights",
    mode: str = "final",
    inspect_classes: bool = False,
) -> AssetCheckReport:
    if mode not in {"final", "development"}:
        raise ValueError("mode must be final or development")
    payload = load_runtime_asset_manifest(manifest_path)
    root = Path(asset_root)
    issues: list[AssetIssue] = []
    for asset in payload["assets"]:
        asset_id = str(asset.get("id", "<unknown>"))
        required_fields = (
            "role", "filename", "source", "license", "model_version",
            "expected_classes", "class_inspection", "availability",
        )
        missing_metadata = [name for name in required_fields if not asset.get(name)]
        if missing_metadata:
            issues.append(AssetIssue(asset_id, "invalid_metadata", ", ".join(missing_metadata)))
            continue
        expected_classes = asset["expected_classes"]
        if not isinstance(expected_classes, list) or not all(
            isinstance(value, str) and value for value in expected_classes
        ):
            issues.append(AssetIssue(asset_id, "invalid_class_mapping", "expected_classes must be non-empty strings"))
        expected_sha = asset.get("sha256")
        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            issues.append(AssetIssue(asset_id, "unfrozen_checksum", "a 64-character SHA256 is required"))
            continue
        path = root / str(asset["filename"])
        if not path.is_file():
            issues.append(AssetIssue(asset_id, "missing", str(path)))
            continue
        actual_sha = sha256_file(path)
        if actual_sha != expected_sha:
            issues.append(AssetIssue(asset_id, "checksum_mismatch", f"expected {expected_sha}, got {actual_sha}"))
            continue
        if inspect_classes:
            class_issue = _inspect_class_mapping(asset, path)
            if class_issue is not None:
                code, message = class_issue
                issues.append(AssetIssue(asset_id, code, message))
    if mode == "development":
        blocking = {"invalid_metadata", "invalid_class_mapping", "checksum_mismatch", "class_mapping_mismatch"}
        issues = [issue for issue in issues if issue.code in blocking]
    return AssetCheckReport(
        mode=mode,
        manifest_version=str(payload["model_bundle_version"]),
        checked_assets=len(payload["assets"]),
        issues=tuple(issues),
    )


def _inspect_class_mapping(asset: dict[str, Any], path: Path) -> tuple[str, str] | None:
    method = asset["class_inspection"]
    expected = list(asset["expected_classes"])
    try:
        if method == "torch_class_names":
            import torch
            checkpoint = torch.load(path, map_location="cpu", weights_only=False)
            actual = checkpoint.get("class_names") if isinstance(checkpoint, dict) else None
        elif method == "ultralytics_names":
            from ultralytics import YOLO
            names = YOLO(str(path)).names
            actual = list(names.values()) if isinstance(names, dict) else list(names)
        elif method == "sidecar_json":
            sidecar = path.with_suffix(path.suffix + ".json")
            actual = json.loads(sidecar.read_text(encoding="utf-8"))["class_names"]
        else:
            return "class_inspection_failed", f"unknown inspection method: {method}"
    except Exception as exc:
        return "class_inspection_failed", f"could not inspect checkpoint classes: {exc}"
    matches = all(value in actual for value in expected) if asset.get("class_match") == "contains" else actual == expected
    if not matches:
        return "class_mapping_mismatch", f"expected {expected}, got {actual}"
    return None
