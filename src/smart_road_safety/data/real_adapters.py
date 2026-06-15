from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from ..manifest import DatasetManifest
from .adapters import DatasetAdapter, DatasetInventory, DatasetMediaSample, IngestionPlan


# ---------------------------------------------------------------------------
# Unified driver-behaviour label taxonomy
# ---------------------------------------------------------------------------

STATE_FARM_CLASS_NAMES: dict[str, str] = {
    "c0": "safe_driving",
    "c1": "texting_right",
    "c2": "phone_right",
    "c3": "texting_left",
    "c4": "phone_left",
    "c5": "operating_radio",
    "c6": "drinking",
    "c7": "reaching_behind",
    "c8": "hair_and_makeup",
    "c9": "talking_to_passenger",
}

DRIVER_SVT_STATES: tuple[str, ...] = (
    "Normal",
    "Camera off",
    "Distraction",
    "Unfastened belt",
    "Drowsiness",
    "No attention",
    "Using phone",
    "Eating",
    "Smoking",
)


# ---------------------------------------------------------------------------
# Common record types for the new datasets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateFarmSample:
    """One labelled image from the State Farm dataset."""

    subject: str
    class_id: str
    class_name: str
    image_path: str

    @property
    def sample_id(self) -> str:
        return f"{self.subject}_{self.class_id}_{Path(self.image_path).stem}"


@dataclass(frozen=True)
class StateFarmInventory:
    """Inventory of the State Farm Distracted Driver dataset."""

    dataset_root: str
    train_samples: tuple[StateFarmSample, ...]
    test_image_paths: tuple[str, ...]
    subjects: tuple[str, ...]

    @property
    def train_count(self) -> int:
        return len(self.train_samples)

    @property
    def test_count(self) -> int:
        return len(self.test_image_paths)

    def get_sample(self, sample_id: str) -> StateFarmSample:
        for sample in self.train_samples:
            if (
                sample.sample_id == sample_id
                or Path(sample.image_path).stem == sample_id
            ):
                return sample
        raise ValueError(f"Unknown State Farm sample_id: {sample_id}")


@dataclass(frozen=True)
class DMDSession:
    """One DMD recording session (single subject, single recording group)."""

    session_id: str
    group: str
    subject_id: str
    session_number: str
    annotation_path: str
    video_paths: dict[str, str] = field(default_factory=dict)
    frame_count: int = 0
    action_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class DMDInventory:
    """Inventory of a DMD subset (distraction or drowsiness)."""

    dataset_root: str
    subset_name: str
    sessions: tuple[DMDSession, ...]

    @property
    def session_count(self) -> int:
        return len(self.sessions)

    def get_session(self, sample_id: str) -> DMDSession:
        for session in self.sessions:
            if session.session_id == sample_id:
                return session
        raise ValueError(f"Unknown DMD session sample_id: {sample_id}")


@dataclass(frozen=True)
class DriverSVTStats:
    """Summary statistics for the DriverSVT dataset."""

    dataset_root: str
    csv_path: str
    total_rows: int
    unique_users: int
    state_counts: dict[str, int]
    columns: tuple[str, ...]


@dataclass(frozen=True)
class DriverSVTRow:
    """One DriverSVT telemetry row selected by CSV row id."""

    row_id: str
    user_id: str
    dangerous_state: str
    speed: float | None
    source_ref: str
    features: dict[str, str]


# ---------------------------------------------------------------------------
# State Farm Adapter
# ---------------------------------------------------------------------------


class StateFarmAdapter(DatasetAdapter):
    adapter_key = "state_farm_distracted_driver"

    @classmethod
    def supports_manifest(cls, manifest: DatasetManifest) -> bool:
        return (
            manifest.sample_unit == "frame"
            and manifest.annotation_format == "folder_class_csv"
        )

    def build_ingestion_plan(self) -> IngestionPlan:
        return IngestionPlan(
            adapter_key=self.adapter_key,
            dataset_root=self._dataset_root_value(),
            sample_unit=self.manifest.sample_unit,
            annotation_format=self.manifest.annotation_format,
            required_assets=("imgs/train/c{0-9}/ folders", "driver_imgs_list.csv"),
            expected_splits=self._split_names(),
            target_families=self.manifest.targets,
            notes=(
                "22,424 training images across 10 distraction classes from 26 drivers.",
                "79,726 unlabeled test images.",
                "Validation should be grouped by labelled train subject; test labels are not available.",
            ),
        )

    def load_inventory(self) -> DatasetInventory:
        if self.dataset_root is None:
            raise ValueError("dataset_root is required to load the State Farm dataset.")
        samples = self._load_train_samples()
        media_samples = tuple(
            DatasetMediaSample(
                sample_id=s.sample_id,
                video_path="",
                screenshot_paths=(s.image_path,),
                label=s.class_name,
                metadata={
                    "subject": s.subject,
                    "class_id": s.class_id,
                    "class_name": s.class_name,
                },
            )
            for s in samples[:25]
        )
        return DatasetInventory(
            dataset_root=str(self.dataset_root),
            sample_unit="frame",
            sample_count=len(samples),
            samples=media_samples,
            notes=(
                f"State Farm: {len(samples)} labelled training images.",
                (
                    "Inventory samples are a deterministic preview; use "
                    "StateFarmInventory for the full labelled set."
                ),
            ),
        )

    def load_state_farm_inventory(self) -> StateFarmInventory:
        """Load full State Farm specific inventory with class labels."""
        if self.dataset_root is None:
            raise ValueError("dataset_root is required.")
        train_samples = self._load_train_samples()
        test_paths = self._load_test_paths()
        subjects = tuple(sorted({s.subject for s in train_samples}))
        return StateFarmInventory(
            dataset_root=str(self.dataset_root),
            train_samples=train_samples,
            test_image_paths=test_paths,
            subjects=subjects,
        )

    def _load_train_samples(self) -> tuple[StateFarmSample, ...]:
        assert self.dataset_root is not None
        csv_path = self.dataset_root / "driver_imgs_list.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing driver_imgs_list.csv at {csv_path}")
        samples: list[StateFarmSample] = []
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                class_id = row["classname"]
                class_name = STATE_FARM_CLASS_NAMES.get(class_id, class_id)
                image_path = str(
                    self.dataset_root / "imgs" / "train" / class_id / row["img"]
                )
                samples.append(
                    StateFarmSample(
                        subject=row["subject"],
                        class_id=class_id,
                        class_name=class_name,
                        image_path=image_path,
                    )
                )
        return tuple(samples)

    def _load_test_paths(self) -> tuple[str, ...]:
        assert self.dataset_root is not None
        test_dir = self.dataset_root / "imgs" / "test"
        if not test_dir.exists():
            return ()
        return tuple(str(p) for p in sorted(test_dir.glob("*.jpg")))


# ---------------------------------------------------------------------------
# DMD Distraction / Drowsiness Adapters
# ---------------------------------------------------------------------------


def _discover_dmd_sessions(
    dataset_root: Path,
    annotation_suffix: str,
) -> tuple[DMDSession, ...]:
    """Walk a DMD-style directory tree and discover recording sessions."""
    sessions: list[DMDSession] = []
    ann_files = sorted(dataset_root.rglob(f"*{annotation_suffix}"))

    for ann_path in ann_files:
        if ann_path.name.startswith("._"):
            continue
        session_dir = ann_path.parent
        filename_prefix = ann_path.name.split("_rgb_ann_")[0]
        prefix_parts = filename_prefix.split("_")
        if len(prefix_parts) >= 3:
            group = prefix_parts[0]
            subject_id = prefix_parts[1]
            session_number = prefix_parts[2]
            session_id = f"{group}_{subject_id}_{session_number}"
        else:
            parts = session_dir.relative_to(dataset_root).parts
            group = parts[-3] if len(parts) >= 3 else "unknown"
            subject_id = parts[-2] if len(parts) >= 2 else "unknown"
            session_number = parts[-1] if len(parts) >= 1 else "unknown"
            session_id = f"{group}_{subject_id}_{session_number}"

        video_paths: dict[str, str] = {}
        for cam in ("face", "body", "hands"):
            cam_files = list(session_dir.glob(f"*_rgb_{cam}.mp4"))
            if cam_files:
                video_paths[cam] = str(cam_files[0])
        mosaic_files = list(session_dir.glob("*_rgb_mosaic.avi"))
        if mosaic_files:
            video_paths["mosaic"] = str(mosaic_files[0])

        frame_count = 0
        action_types: list[str] = []
        try:
            ann_data = json.loads(ann_path.read_text(encoding="utf-8"))
            ol = ann_data.get("openlabel", ann_data.get("vcd", {}))
            frames = ol.get("frames", {})
            frame_count = len(frames)
            actions = ol.get("actions", {})
            action_types = sorted(
                {str(act.get("type", "unknown")) for act in actions.values()}
            )
        except (json.JSONDecodeError, KeyError):
            pass

        sessions.append(
            DMDSession(
                session_id=session_id,
                group=group,
                subject_id=subject_id,
                session_number=session_number,
                annotation_path=str(ann_path),
                video_paths=video_paths,
                frame_count=frame_count,
                action_types=tuple(action_types),
            )
        )

    return tuple(sessions)


class DMDDistractionAdapter(DatasetAdapter):
    adapter_key = "dmd_distraction"

    @classmethod
    def supports_manifest(cls, manifest: DatasetManifest) -> bool:
        return (
            manifest.sample_unit == "video_clip"
            and manifest.annotation_format == "openlabel_json"
            and "distraction" in manifest.targets
        )

    def build_ingestion_plan(self) -> IngestionPlan:
        return IngestionPlan(
            adapter_key=self.adapter_key,
            dataset_root=self._dataset_root_value(),
            sample_unit=self.manifest.sample_unit,
            annotation_format=self.manifest.annotation_format,
            required_assets=(
                "dmd/g{group}/{subject}/s{session}/ directories",
                "*_rgb_ann_distraction.json annotation files",
                "*_rgb_{face,body,hands}.mp4 video files",
            ),
            expected_splits=self._split_names(),
            target_families=self.manifest.targets,
            notes=(
                "DMD distraction subset with frame-level OpenLABEL annotations.",
                "Actions include gaze, safe_drive, talking, reach_backseat, hand-wheel states.",
            ),
        )

    def load_inventory(self) -> DatasetInventory:
        if self.dataset_root is None:
            raise ValueError("dataset_root is required for DMD distraction.")
        sessions = _discover_dmd_sessions(
            self.dataset_root, "_rgb_ann_distraction.json"
        )
        media_samples = tuple(
            DatasetMediaSample(
                sample_id=s.session_id,
                video_path=s.video_paths.get("face", s.video_paths.get("body", "")),
                screenshot_paths=(),
                label=_primary_dmd_label(s.action_types),
                metadata={
                    "group": s.group,
                    "subject_id": s.subject_id,
                    "session_number": s.session_number,
                    "frame_count": str(s.frame_count),
                    "action_types": "|".join(s.action_types),
                },
            )
            for s in sessions
        )
        return DatasetInventory(
            dataset_root=str(self.dataset_root),
            sample_unit="video_clip",
            sample_count=len(sessions),
            samples=media_samples,
            notes=(
                f"DMD distraction: {len(sessions)} sessions discovered.",
            ),
        )

    def load_dmd_inventory(self) -> DMDInventory:
        """Load the full DMD-specific inventory."""
        if self.dataset_root is None:
            raise ValueError("dataset_root is required.")
        sessions = _discover_dmd_sessions(
            self.dataset_root, "_rgb_ann_distraction.json"
        )
        return DMDInventory(
            dataset_root=str(self.dataset_root),
            subset_name="distraction",
            sessions=sessions,
        )


class DMDDrowsinessAdapter(DatasetAdapter):
    adapter_key = "dmd_drowsiness"

    @classmethod
    def supports_manifest(cls, manifest: DatasetManifest) -> bool:
        return (
            manifest.sample_unit == "video_clip"
            and manifest.annotation_format == "openlabel_json"
            and "drowsiness" in manifest.targets
        )

    def build_ingestion_plan(self) -> IngestionPlan:
        return IngestionPlan(
            adapter_key=self.adapter_key,
            dataset_root=self._dataset_root_value(),
            sample_unit=self.manifest.sample_unit,
            annotation_format=self.manifest.annotation_format,
            required_assets=(
                "dmd/g{group}/{subject}/s{session}/ directories",
                "*_rgb_ann_drowsiness.json annotation files",
                "*_rgb_{face,body,hands}.mp4 video files",
            ),
            expected_splits=self._split_names(),
            target_families=self.manifest.targets,
            notes=(
                "DMD drowsiness subset with frame-level OpenLABEL annotations.",
                "Actions include eye_state (open/close/opening/closing), blinking, yawning.",
            ),
        )

    def load_inventory(self) -> DatasetInventory:
        if self.dataset_root is None:
            raise ValueError("dataset_root is required for DMD drowsiness.")
        sessions = _discover_dmd_sessions(
            self.dataset_root, "_rgb_ann_drowsiness.json"
        )
        media_samples = tuple(
            DatasetMediaSample(
                sample_id=s.session_id,
                video_path=s.video_paths.get("face", s.video_paths.get("body", "")),
                screenshot_paths=(),
                label=_primary_dmd_label(s.action_types),
                metadata={
                    "group": s.group,
                    "subject_id": s.subject_id,
                    "session_number": s.session_number,
                    "frame_count": str(s.frame_count),
                    "action_types": "|".join(s.action_types),
                },
            )
            for s in sessions
        )
        return DatasetInventory(
            dataset_root=str(self.dataset_root),
            sample_unit="video_clip",
            sample_count=len(sessions),
            samples=media_samples,
            notes=(
                f"DMD drowsiness: {len(sessions)} sessions discovered.",
            ),
        )

    def load_dmd_inventory(self) -> DMDInventory:
        """Load the full DMD-specific inventory."""
        if self.dataset_root is None:
            raise ValueError("dataset_root is required.")
        sessions = _discover_dmd_sessions(
            self.dataset_root, "_rgb_ann_drowsiness.json"
        )
        return DMDInventory(
            dataset_root=str(self.dataset_root),
            subset_name="drowsiness",
            sessions=sessions,
        )


# ---------------------------------------------------------------------------
# DriverSVT Adapter
# ---------------------------------------------------------------------------


class DriverSVTAdapter(DatasetAdapter):
    adapter_key = "driver_svt_teknofest"

    @classmethod
    def supports_manifest(cls, manifest: DatasetManifest) -> bool:
        return (
            manifest.sample_unit == "telemetry_row"
            and manifest.annotation_format == "csv_tabular"
        )

    def build_ingestion_plan(self) -> IngestionPlan:
        return IngestionPlan(
            adapter_key=self.adapter_key,
            dataset_root=self._dataset_root_value(),
            sample_unit=self.manifest.sample_unit,
            annotation_format=self.manifest.annotation_format,
            required_assets=("DriverSVT.csv",),
            expected_splits=self._split_names(),
            target_families=self.manifest.targets,
            notes=(
                "17.5M telemetry rows from 633 drivers.",
                (
                    "9 dangerous states including Normal, Distraction, "
                    "Drowsiness, Using phone, Smoking, etc."
                ),
                (
                    "Features: speed, gforce, perclos, head_pose, "
                    "mouth_open_ratio, heart_rate, IMU sensors."
                ),
                "CSV is ~9 GB — must be loaded in chunks for memory efficiency.",
            ),
        )

    def load_inventory(self) -> DatasetInventory:
        if self.dataset_root is None:
            raise ValueError("dataset_root is required for DriverSVT.")
        csv_path = self._find_csv_path()
        declared_count = self.manifest.extra_fields.get("row_count")
        sample_count = int(declared_count) if declared_count is not None else 0
        return DatasetInventory(
            dataset_root=str(self.dataset_root),
            sample_unit="telemetry_row",
            sample_count=sample_count,
            samples=(),
            notes=(
                (
                    f"DriverSVT CSV at {csv_path}. Use load_svt_stats(), "
                    "load_row(), or iterate_chunks() for real access."
                ),
                "Samples are not materialized in inventory because the CSV has 17,561,501 rows.",
            ),
        )

    def load_svt_stats(self, max_rows: int | None = None) -> DriverSVTStats:
        """Scan the CSV and return summary statistics."""
        if self.dataset_root is None:
            raise ValueError("dataset_root is required.")
        csv_path = self._find_csv_path()
        from collections import Counter

        state_counts: Counter[str] = Counter()
        users: set[str] = set()
        columns: tuple[str, ...] = ()
        row_count = 0

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = tuple(reader.fieldnames or ())
            for row in reader:
                state_counts[row.get("dangerousstate", "MISSING")] += 1
                users.add(row.get("userid", ""))
                row_count += 1
                if max_rows is not None and row_count >= max_rows:
                    break

        return DriverSVTStats(
            dataset_root=str(self.dataset_root),
            csv_path=str(csv_path),
            total_rows=row_count,
            unique_users=len(users),
            state_counts=dict(state_counts.most_common()),
            columns=columns,
        )

    def iterate_chunks(
        self, chunk_size: int = 10000
    ) -> Iterator[list[dict[str, Any]]]:
        """Yield chunks of rows from the CSV for memory-efficient processing."""
        if self.dataset_root is None:
            raise ValueError("dataset_root is required.")
        csv_path = self._find_csv_path()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            chunk: list[dict[str, Any]] = []
            for row in reader:
                chunk.append(dict(row))
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []
            if chunk:
                yield chunk

    def load_row(self, sample_id: str) -> DriverSVTRow:
        """Load one DriverSVT row by stable sample id.

        Accepted formats:
        - ``row:<csv_row_id>``
        - ``driversvt_row:<csv_row_id>``
        - the raw numeric CSV row id
        """
        if self.dataset_root is None:
            raise ValueError("dataset_root is required.")
        target_id = _normalize_driver_svt_sample_id(sample_id)
        csv_path = self._find_csv_path()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_id = str(row.get("", "")).strip()
                if row_id == target_id:
                    speed = _parse_optional_float(row.get("speed"))
                    user_id = str(row.get("userid", "")).strip()
                    dangerous_state = str(row.get("dangerousstate", "")).strip()
                    return DriverSVTRow(
                        row_id=row_id,
                        user_id=user_id,
                        dangerous_state=dangerous_state,
                        speed=speed,
                        source_ref=f"{csv_path}#row:{row_id}",
                        features={
                            key: str(value)
                            for key, value in row.items()
                            if key
                            in {
                                "datetime",
                                "datetimestart",
                                "speed",
                                "gforce",
                                "perclos",
                                "head_pose",
                                "mouth_open_ratio",
                                "heart_rate",
                                "dangerousstate",
                            }
                        },
                    )
        raise ValueError(f"Unknown DriverSVT row sample_id: {sample_id}")

    def _find_csv_path(self) -> Path:
        assert self.dataset_root is not None
        csv_path = self.dataset_root / "DriverSVT.csv"
        if not csv_path.exists():
            csv_files = list(self.dataset_root.glob("*.csv"))
            if not csv_files:
                raise FileNotFoundError(
                    f"No CSV file found in {self.dataset_root}"
                )
            csv_path = csv_files[0]
        return csv_path


def _primary_dmd_label(action_types: tuple[str, ...]) -> str:
    priority = (
        ("driver_actions/texting_left", "texting_left"),
        ("driver_actions/texting_right", "texting_right"),
        ("driver_actions/phonecall_left", "phonecall_left"),
        ("driver_actions/phonecall_right", "phonecall_right"),
        ("driver_actions/drinking", "drinking"),
        ("driver_actions/reach_backseat", "reach_backseat"),
        ("driver_actions/reach_side", "reach_side"),
        ("driver_actions/hair_and_makeup", "hair_and_makeup"),
        ("driver_actions/radio", "operating_radio"),
        ("driver_actions/talking_to_passenger", "talking_to_passenger"),
        ("yawning/Yawning with hand", "yawning_with_hand"),
        ("yawning/Yawning without hand", "yawning_without_hand"),
        ("eyes_state/close", "eyes_closed"),
        ("eyes_state/closing", "eyes_closing"),
        ("blinks/blinking", "blinking"),
    )
    action_set = set(action_types)
    for raw_label, normalized_label in priority:
        if raw_label in action_set:
            return normalized_label
    if "driver_actions/safe_drive" in action_set:
        return "safe_drive"
    return action_types[0].replace("/", "_") if action_types else "unknown"


def _normalize_driver_svt_sample_id(sample_id: str) -> str:
    cleaned = sample_id.strip()
    for prefix in ("row:", "driversvt_row:", "driversvt:row:"):
        if cleaned.startswith(prefix):
            return cleaned.removeprefix(prefix)
    if cleaned.isdigit():
        return cleaned
    raise ValueError(
        "DriverSVT sample_id must be row:<csv_row_id>, "
        "driversvt_row:<csv_row_id>, or a numeric row id."
    )


def _parse_optional_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    return float(value)
