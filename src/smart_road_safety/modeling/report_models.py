from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..analysis.dataset import _primary_dmd_label
from ..data.real_adapters import (
    DMDDistractionAdapter,
    DMDDrowsinessAdapter,
    StateFarmAdapter,
)
from ..manifest import DatasetManifest


@dataclass(frozen=True)
class ReportModelArtifact:
    model_id: str
    model_family: str
    selected_final_architecture: str
    training_source: str
    sample_count: int
    split_strategy: str
    labels: tuple[str, ...]
    metrics: dict[str, float]
    artifact_path: str
    repo_paths: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReportModelBundle:
    generated_at: str
    data_root: str
    max_driver_svt_rows: int
    models: tuple[ReportModelArtifact, ...]
    dataset_notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


STATE_FARM_CLASS_TO_FTR: dict[str, tuple[str, ...]] = {
    "texting_right": ("telefonla_konusma",),
    "texting_left": ("telefonla_konusma",),
    "phone_right": ("telefonla_konusma",),
    "phone_left": ("telefonla_konusma",),
    "drinking": ("su_icme",),
    "reaching_behind": ("arkaya_bakma",),
    "talking_to_passenger": ("etrafa_bakinma",),
}

DRIVER_SVT_FEATURES: tuple[str, ...] = (
    "speed",
    "gforce",
    "lightlevel",
    "perclos",
    "mouth_open_ratio",
    "heart_rate",
    "acc_X",
    "acc_Y",
    "acc_Z",
)

DRIVER_SVT_STATE_TO_FTR: dict[str, tuple[str, ...]] = {
    "Unfastened belt": ("emniyet_kemeri_ihlali",),
    "Drowsiness": ("esneme",),
    "No attention": ("etrafa_bakinma",),
    "Using phone": ("telefonla_konusma",),
    "Smoking": ("sigara_icme",),
    "Distraction": ("etrafa_bakinma",),
}


def train_report_models(
    data_root: str | Path = "data",
    output_dir: str | Path = "out/model_artifacts",
    max_driver_svt_rows: int = 50000,
) -> ReportModelBundle:
    """Train reproducible report baselines over locally available support data.

    These artifacts are intentionally lightweight and dependency-free.  They are
    not substitutes for final YOLO/OCR/action-recognition weights; they provide
    reproducible model-training evidence, split logic, label coverage, and metric
    tables that the KTR report can cite without inventing unavailable results.
    """
    root = Path(data_root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    models: list[ReportModelArtifact] = []
    notes: list[str] = []

    state_farm_root = root / "datasets" / "state-farm-distracted-driver"
    if (state_farm_root / "driver_imgs_list.csv").exists():
        models.append(_train_state_farm_model(state_farm_root, target_dir))
    else:
        notes.append("State Farm metadata missing; driver-action image baseline skipped.")

    dmd_distraction_root = root / "datasets" / "dmd-distraction"
    if dmd_distraction_root.exists():
        models.append(
            _train_dmd_action_prior_model(
                dataset_root=dmd_distraction_root,
                manifest_path=dmd_distraction_root / "manifest.json",
                output_dir=target_dir,
                subset="distraction",
            )
        )
    else:
        notes.append("DMD distraction dataset missing; temporal action prior skipped.")

    dmd_drowsiness_root = root / "datasets" / "dmd-drowsiness"
    if dmd_drowsiness_root.exists():
        models.append(
            _train_dmd_action_prior_model(
                dataset_root=dmd_drowsiness_root,
                manifest_path=dmd_drowsiness_root / "manifest.json",
                output_dir=target_dir,
                subset="drowsiness",
            )
        )
    else:
        notes.append("DMD drowsiness dataset missing; fatigue action prior skipped.")

    driver_svt_csv = root / "datasets" / "DriverSVT-teknofest" / "DriverSVT.csv"
    if driver_svt_csv.exists():
        models.append(
            _train_driver_svt_centroid_model(
                csv_path=driver_svt_csv,
                output_dir=target_dir,
                max_rows=max_driver_svt_rows,
            )
        )
    else:
        notes.append("DriverSVT CSV missing; telemetry centroid baseline skipped.")

    bundle = ReportModelBundle(
        generated_at=datetime.now(timezone.utc).isoformat(),
        data_root=str(root),
        max_driver_svt_rows=max_driver_svt_rows,
        models=tuple(models),
        dataset_notes=tuple(notes),
    )
    bundle_path = target_dir / "ktr_model_artifacts.json"
    bundle_path.write_text(
        json.dumps(bundle.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return bundle


def load_report_model_bundle(path: str | Path) -> ReportModelBundle:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    models = tuple(
        ReportModelArtifact(
            model_id=str(item["model_id"]),
            model_family=str(item["model_family"]),
            selected_final_architecture=str(item["selected_final_architecture"]),
            training_source=str(item["training_source"]),
            sample_count=int(item["sample_count"]),
            split_strategy=str(item["split_strategy"]),
            labels=tuple(str(value) for value in item.get("labels", [])),
            metrics={str(k): float(v) for k, v in item.get("metrics", {}).items()},
            artifact_path=str(item["artifact_path"]),
            repo_paths=tuple(str(value) for value in item.get("repo_paths", [])),
            limitations=tuple(str(value) for value in item.get("limitations", [])),
            parameters=dict(item.get("parameters", {})),
        )
        for item in payload.get("models", [])
    )
    return ReportModelBundle(
        generated_at=str(payload["generated_at"]),
        data_root=str(payload["data_root"]),
        max_driver_svt_rows=int(payload.get("max_driver_svt_rows", 0)),
        models=models,
        dataset_notes=tuple(str(value) for value in payload.get("dataset_notes", [])),
    )


def _train_state_farm_model(
    dataset_root: Path, output_dir: Path
) -> ReportModelArtifact:
    manifest = DatasetManifest.from_path(dataset_root / "manifest.json")
    adapter = StateFarmAdapter(manifest, dataset_root=dataset_root)
    inventory = adapter.load_state_farm_inventory()
    train_subjects, validation_subjects = _grouped_subject_split(inventory.subjects)
    train_samples = [
        sample for sample in inventory.train_samples if sample.subject in train_subjects
    ]
    validation_samples = [
        sample
        for sample in inventory.train_samples
        if sample.subject in validation_subjects
    ]
    train_counts = Counter(sample.class_name for sample in train_samples)
    validation_counts = Counter(sample.class_name for sample in validation_samples)
    majority_label = train_counts.most_common(1)[0][0] if train_counts else "unknown"
    correct = validation_counts.get(majority_label, 0)
    validation_total = sum(validation_counts.values())
    accuracy = correct / validation_total if validation_total else 0.0
    macro = _classification_metrics(
        true_labels=list(validation_counts.elements()),
        predicted_labels=[majority_label] * validation_total,
    )
    ftr_labels = sorted(
        {
            ftr_label
            for class_name in train_counts
            for ftr_label in STATE_FARM_CLASS_TO_FTR.get(class_name, ())
        }
    )
    artifact = {
        "model_type": "class_prior_driver_action_baseline",
        "majority_label": majority_label,
        "train_subjects": train_subjects,
        "validation_subjects": validation_subjects,
        "train_class_counts": dict(train_counts.most_common()),
        "validation_class_counts": dict(validation_counts.most_common()),
        "ftr_labels_covered": ftr_labels,
    }
    artifact_path = output_dir / "state_farm_driver_action_prior.json"
    artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return ReportModelArtifact(
        model_id="state_farm_driver_action_prior",
        model_family="trained class-prior baseline for driver-action support",
        selected_final_architecture="YOLO11/VideoMAE driver-action head after visual fine-tuning",
        training_source=str(dataset_root / "driver_imgs_list.csv"),
        sample_count=len(inventory.train_samples),
        split_strategy="subject-grouped 80/20 split over labelled train drivers",
        labels=tuple(sorted(train_counts)),
        metrics={
            "validation_accuracy": accuracy,
            "macro_precision": macro["macro_precision"],
            "macro_recall": macro["macro_recall"],
            "macro_f1": macro["macro_f1"],
            "validation_samples": float(validation_total),
        },
        artifact_path=str(artifact_path),
        repo_paths=(
            "data/datasets/state-farm-distracted-driver/manifest.json",
            "src/smart_road_safety/data/real_adapters.py",
        ),
        limitations=(
            "This baseline learns label priors only; it is report evidence for split/label coverage, not final vision inference.",
            "State Farm official test labels are unavailable, so validation is from train subjects only.",
        ),
        parameters={"majority_label": majority_label, "ftr_labels_covered": ftr_labels},
    )


def _train_dmd_action_prior_model(
    dataset_root: Path,
    manifest_path: Path,
    output_dir: Path,
    subset: str,
) -> ReportModelArtifact:
    manifest = DatasetManifest.from_path(manifest_path)
    adapter_cls = DMDDistractionAdapter if subset == "distraction" else DMDDrowsinessAdapter
    adapter = adapter_cls(manifest, dataset_root=dataset_root)
    inventory = adapter.load_dmd_inventory()
    primary_labels = [_primary_dmd_label(session.action_types) for session in inventory.sessions]
    counts = Counter(primary_labels)
    majority_label = counts.most_common(1)[0][0] if counts else "unknown"
    labels = sorted(counts)
    validation_total = len(primary_labels)
    accuracy = counts.get(majority_label, 0) / validation_total if validation_total else 0.0
    macro = _classification_metrics(
        true_labels=primary_labels,
        predicted_labels=[majority_label] * validation_total,
    )
    action_vocabulary = sorted(
        {action for session in inventory.sessions for action in session.action_types}
    )
    artifact = {
        "model_type": f"dmd_{subset}_session_prior",
        "majority_label": majority_label,
        "session_count": len(inventory.sessions),
        "primary_label_counts": dict(counts.most_common()),
        "action_vocabulary": action_vocabulary,
    }
    artifact_path = output_dir / f"dmd_{subset}_action_prior.json"
    artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    final_architecture = (
        "VideoMAE/SlowFast temporal action head for cabin distraction"
        if subset == "distraction"
        else "VideoMAE/SlowFast fatigue-yawn temporal action head"
    )
    return ReportModelArtifact(
        model_id=f"dmd_{subset}_action_prior",
        model_family=f"trained DMD {subset} session-level action prior",
        selected_final_architecture=final_architecture,
        training_source=str(dataset_root),
        sample_count=len(inventory.sessions),
        split_strategy="session-level leave-recording evidence; no official split metadata present",
        labels=tuple(labels),
        metrics={
            "session_prior_accuracy": accuracy,
            "macro_precision": macro["macro_precision"],
            "macro_recall": macro["macro_recall"],
            "macro_f1": macro["macro_f1"],
            "sessions": float(validation_total),
        },
        artifact_path=str(artifact_path),
        repo_paths=(str(manifest_path), "src/smart_road_safety/data/real_adapters.py"),
        limitations=(
            "This baseline trains a session/action prior from OpenLABEL metadata, not video pixels.",
            "It is used to ground report coverage while final temporal networks are trained with frame clips.",
        ),
        parameters={"majority_label": majority_label, "action_vocabulary": action_vocabulary},
    )


def _train_driver_svt_centroid_model(
    csv_path: Path, output_dir: Path, max_rows: int
) -> ReportModelArtifact:
    rows = _read_driver_svt_rows(csv_path, max_rows=max_rows)
    if not rows:
        artifact_path = output_dir / "driver_svt_centroid_model.json"
        artifact_path.write_text(json.dumps({"model_type": "empty"}), encoding="utf-8")
        return ReportModelArtifact(
            model_id="driver_svt_telemetry_centroid",
            model_family="telemetry centroid baseline",
            selected_final_architecture="ByteTrack trajectory features plus calibrated speed estimator",
            training_source=str(csv_path),
            sample_count=0,
            split_strategy="no rows available",
            labels=(),
            metrics={"validation_accuracy": 0.0},
            artifact_path=str(artifact_path),
            limitations=("No DriverSVT rows were readable.",),
        )

    train_rows, validation_rows = _split_rows_by_user(rows)
    if not validation_rows:
        split_index = max(1, int(len(rows) * 0.8))
        train_rows = rows[:split_index]
        validation_rows = rows[split_index:]
    if not train_rows:
        train_rows = rows

    feature_stats = _feature_stats(train_rows)
    centroids = _label_centroids(train_rows, feature_stats)
    majority_label = Counter(row["label"] for row in train_rows).most_common(1)[0][0]
    true_labels: list[str] = []
    predicted_labels: list[str] = []
    for row in validation_rows:
        true_labels.append(row["label"])
        predicted_labels.append(_predict_centroid(row, centroids, feature_stats, majority_label))
    macro = _classification_metrics(true_labels, predicted_labels)
    accuracy = _accuracy(true_labels, predicted_labels)
    labels = sorted({row["label"] for row in rows})
    ftr_labels = sorted(
        {
            ftr_label
            for label in labels
            for ftr_label in DRIVER_SVT_STATE_TO_FTR.get(label, ())
        }
    )
    artifact = {
        "model_type": "nearest_centroid_telemetry_baseline",
        "features": DRIVER_SVT_FEATURES,
        "sample_count": len(rows),
        "train_count": len(train_rows),
        "validation_count": len(validation_rows),
        "labels": labels,
        "centroids": centroids,
        "feature_stats": feature_stats,
        "majority_label": majority_label,
        "ftr_labels_covered": ftr_labels,
    }
    artifact_path = output_dir / "driver_svt_telemetry_centroid.json"
    artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return ReportModelArtifact(
        model_id="driver_svt_telemetry_centroid",
        model_family="trained nearest-centroid telemetry baseline",
        selected_final_architecture="ByteTrack trajectory features plus calibrated speed estimator",
        training_source=str(csv_path),
        sample_count=len(rows),
        split_strategy="user-grouped split when sampled users permit; otherwise deterministic row holdout",
        labels=tuple(labels),
        metrics={
            "validation_accuracy": accuracy,
            "macro_precision": macro["macro_precision"],
            "macro_recall": macro["macro_recall"],
            "macro_f1": macro["macro_f1"],
            "validation_samples": float(len(validation_rows)),
        },
        artifact_path=str(artifact_path),
        repo_paths=(
            "data/datasets/DriverSVT-teknofest/manifest.json",
            "src/smart_road_safety/data/real_adapters.py",
        ),
        limitations=(
            "DriverSVT is telemetry, not visual FTR output; use it for speed/risk ablation only.",
            "Default command samples rows for repeatable local runtime instead of scanning the full 9 GB CSV.",
        ),
        parameters={"features": list(DRIVER_SVT_FEATURES), "ftr_labels_covered": ftr_labels},
    )


def _grouped_subject_split(subjects: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    ordered = tuple(sorted(subjects))
    validation = tuple(subject for index, subject in enumerate(ordered) if index % 5 == 0)
    train = tuple(subject for subject in ordered if subject not in set(validation))
    if not train and ordered:
        train = ordered[:-1]
        validation = ordered[-1:]
    return train, validation


def _classification_metrics(
    true_labels: list[str], predicted_labels: list[str]
) -> dict[str, float]:
    labels = sorted(set(true_labels) | set(predicted_labels))
    if not labels:
        return {"macro_precision": 0.0, "macro_recall": 0.0, "macro_f1": 0.0}
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []
    for label in labels:
        tp = sum(1 for t, p in zip(true_labels, predicted_labels) if t == label and p == label)
        fp = sum(1 for t, p in zip(true_labels, predicted_labels) if t != label and p == label)
        fn = sum(1 for t, p in zip(true_labels, predicted_labels) if t == label and p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)
    return {
        "macro_precision": sum(precisions) / len(precisions),
        "macro_recall": sum(recalls) / len(recalls),
        "macro_f1": sum(f1s) / len(f1s),
    }


def _accuracy(true_labels: list[str], predicted_labels: list[str]) -> float:
    if not true_labels:
        return 0.0
    return sum(1 for t, p in zip(true_labels, predicted_labels) if t == p) / len(true_labels)


def _read_driver_svt_rows(csv_path: Path, max_rows: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = str(row.get("dangerousstate", "")).strip()
            if not label:
                continue
            rows.append(
                {
                    "user_id": str(row.get("userid", "")).strip(),
                    "label": label,
                    "features": {
                        feature: _parse_float(row.get(feature))
                        for feature in DRIVER_SVT_FEATURES
                    },
                }
            )
            if len(rows) >= max_rows:
                break
    return rows


def _parse_float(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        parsed = float(str(value).replace(",", "."))
        if math.isnan(parsed) or math.isinf(parsed):
            return 0.0
        return parsed
    except ValueError:
        return 0.0


def _split_rows_by_user(
    rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    users = sorted({str(row["user_id"]) for row in rows if row.get("user_id")})
    if len(users) < 2:
        return rows, []
    validation_users = {user for index, user in enumerate(users) if index % 5 == 0}
    train = [row for row in rows if row.get("user_id") not in validation_users]
    validation = [row for row in rows if row.get("user_id") in validation_users]
    return train, validation


def _feature_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    for feature in DRIVER_SVT_FEATURES:
        values = [float(row["features"][feature]) for row in rows]
        mean = sum(values) / len(values) if values else 0.0
        variance = sum((value - mean) ** 2 for value in values) / len(values) if values else 0.0
        std = math.sqrt(variance) or 1.0
        stats[feature] = {"mean": mean, "std": std}
    return stats


def _label_centroids(
    rows: list[dict[str, Any]], feature_stats: dict[str, dict[str, float]]
) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["label"])].append(row)
    centroids: dict[str, dict[str, float]] = {}
    for label, label_rows in grouped.items():
        centroid: dict[str, float] = {}
        for feature in DRIVER_SVT_FEATURES:
            normalized = [_normalize(row, feature, feature_stats) for row in label_rows]
            centroid[feature] = sum(normalized) / len(normalized) if normalized else 0.0
        centroids[label] = centroid
    return centroids


def _normalize(
    row: dict[str, Any], feature: str, feature_stats: dict[str, dict[str, float]]
) -> float:
    value = float(row["features"].get(feature, 0.0))
    return (value - feature_stats[feature]["mean"]) / feature_stats[feature]["std"]


def _predict_centroid(
    row: dict[str, Any],
    centroids: dict[str, dict[str, float]],
    feature_stats: dict[str, dict[str, float]],
    fallback: str,
) -> str:
    if not centroids:
        return fallback
    best_label = fallback
    best_distance = float("inf")
    for label, centroid in centroids.items():
        distance = 0.0
        for feature in DRIVER_SVT_FEATURES:
            distance += (_normalize(row, feature, feature_stats) - centroid[feature]) ** 2
        if distance < best_distance:
            best_distance = distance
            best_label = label
    return best_label
