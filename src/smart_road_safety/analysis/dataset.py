from __future__ import annotations

from pathlib import Path

from ..data import (
    DMDDistractionAdapter,
    DMDDrowsinessAdapter,
    DriverSVTAdapter,
    StateFarmAdapter,
    build_adapter_from_manifest_path,
)
from .models import AnalysisResult, DatasetSelection
from .observations import ObservationRegistry


_STATE_FARM_RISK_SCORES: dict[str, float] = {
    "safe_driving": 0.05,
    "texting_right": 0.90,
    "texting_left": 0.90,
    "phone_right": 0.88,
    "phone_left": 0.88,
    "operating_radio": 0.70,
    "drinking": 0.82,
    "reaching_behind": 0.84,
    "hair_and_makeup": 0.76,
    "talking_to_passenger": 0.66,
}

_DRIVER_SVT_RISK_SCORES: dict[str, float] = {
    "Normal": 0.05,
    "Camera off": 0.70,
    "Distraction": 0.82,
    "Unfastened belt": 0.74,
    "Drowsiness": 0.92,
    "No attention": 0.88,
    "Using phone": 0.90,
    "Eating": 0.78,
    "Smoking": 0.80,
}

_DMD_RISK_SCORES: dict[str, float] = {
    "safe_drive": 0.05,
    "texting_left": 0.90,
    "texting_right": 0.90,
    "phonecall_left": 0.86,
    "phonecall_right": 0.86,
    "drinking": 0.82,
    "reach_backseat": 0.84,
    "reach_side": 0.74,
    "hair_and_makeup": 0.76,
    "operating_radio": 0.70,
    "talking_to_passenger": 0.66,
    "yawning_with_hand": 0.92,
    "yawning_without_hand": 0.90,
    "eyes_closed": 0.91,
    "eyes_closing": 0.82,
    "blinking": 0.62,
}


def build_dataset_backed_analysis_result(
    dataset_selection: DatasetSelection,
) -> AnalysisResult:
    """Build an analysis result from a real dataset sample selection.

    This is not model inference. It maps authoritative dataset ground truth into the
    stable analysis/orchestration contract so CLI, API, evaluation, export, and
    telecom orchestration operate on real dataset facts while model training remains
    a future replacement behind the same boundary.
    """
    adapter = build_adapter_from_manifest_path(
        manifest_path=dataset_selection.manifest_path,
        dataset_root=dataset_selection.dataset_root,
    )

    if isinstance(adapter, StateFarmAdapter):
        return _build_state_farm_result(adapter, dataset_selection.sample_id)
    if isinstance(adapter, (DMDDistractionAdapter, DMDDrowsinessAdapter)):
        return _build_dmd_result(adapter, dataset_selection.sample_id)
    if isinstance(adapter, DriverSVTAdapter):
        return _build_driver_svt_result(adapter, dataset_selection.sample_id)

    return _build_legacy_observed_media_result(dataset_selection)


def _build_state_farm_result(
    adapter: StateFarmAdapter, sample_id: str
) -> AnalysisResult:
    inventory = adapter.load_state_farm_inventory()
    sample = inventory.get_sample(sample_id)
    risk_score = _STATE_FARM_RISK_SCORES.get(sample.class_name, 0.75)
    summary = (
        "State Farm ground truth maps this image to "
        f"{sample.class_name.replace('_', ' ')}."
    )
    return AnalysisResult(
        source_ref=sample.image_path,
        quality_profile="standard",
        target_vehicle_detected=False,
        target_vehicle_confidence=0.0,
        plate_candidate_detected=False,
        plate_visibility_score=0.0,
        driver_risk_score=risk_score,
        driver_risk_label=sample.class_name,
        distance_meters=None,
        summary_message=summary,
        notes=(
            "dataset=state_farm_distracted_driver",
            f"sample_id={sample.sample_id}",
            f"subject={sample.subject}",
            f"class_id={sample.class_id}",
            "ground_truth=folder_class_csv",
        ),
    )


def _build_dmd_result(
    adapter: DMDDistractionAdapter | DMDDrowsinessAdapter, sample_id: str
) -> AnalysisResult:
    inventory = adapter.load_dmd_inventory()
    session = inventory.get_session(sample_id)
    label = _primary_dmd_label(session.action_types)
    risk_score = _DMD_RISK_SCORES.get(label, 0.75)
    subset_name = inventory.subset_name
    source_ref = session.video_paths.get("face") or next(
        iter(session.video_paths.values()), session.annotation_path
    )
    summary = (
        f"DMD {subset_name} OpenLABEL annotations map session "
        f"{session.session_id} to {label.replace('_', ' ')}."
    )
    return AnalysisResult(
        source_ref=source_ref,
        quality_profile="standard",
        target_vehicle_detected=False,
        target_vehicle_confidence=0.0,
        plate_candidate_detected=False,
        plate_visibility_score=0.0,
        driver_risk_score=risk_score,
        driver_risk_label=label,
        distance_meters=None,
        summary_message=summary,
        notes=(
            f"dataset=dmd_{subset_name}",
            f"sample_id={session.session_id}",
            f"annotation_path={session.annotation_path}",
            f"frame_count={session.frame_count}",
            "ground_truth=openlabel_json",
            "action_types=" + "|".join(session.action_types),
        ),
    )


def _build_driver_svt_result(
    adapter: DriverSVTAdapter, sample_id: str
) -> AnalysisResult:
    row = adapter.load_row(sample_id)
    risk_score = _DRIVER_SVT_RISK_SCORES.get(row.dangerous_state, 0.75)
    summary = (
        "DriverSVT row-level telemetry labels this sample as "
        f"{row.dangerous_state}."
    )
    speed_note = (
        "speed=missing"
        if row.speed is None
        else f"speed_dataset_native={row.speed:.4f}"
    )
    return AnalysisResult(
        source_ref=row.source_ref,
        quality_profile="standard",
        target_vehicle_detected=False,
        target_vehicle_confidence=0.0,
        plate_candidate_detected=False,
        plate_visibility_score=0.0,
        driver_risk_score=risk_score,
        driver_risk_label=row.dangerous_state,
        distance_meters=None,
        summary_message=summary,
        notes=(
            "dataset=DriverSVT-teknofest",
            f"sample_id=row:{row.row_id}",
            f"user_id={row.user_id}",
            speed_note,
            "ground_truth=csv_tabular.dangerousstate",
        ),
    )


def _build_legacy_observed_media_result(
    dataset_selection: DatasetSelection,
) -> AnalysisResult:
    adapter = build_adapter_from_manifest_path(
        manifest_path=dataset_selection.manifest_path,
        dataset_root=dataset_selection.dataset_root,
    )
    inventory = adapter.load_inventory()
    sample = inventory.get_sample(dataset_selection.sample_id)
    observations_path = (
        Path(dataset_selection.observations_path)
        if dataset_selection.observations_path is not None
        else Path(dataset_selection.dataset_root) / "video_observations.json"
    )
    observation = ObservationRegistry.from_path(observations_path).get_sample(
        dataset_selection.sample_id
    )
    return AnalysisResult(
        source_ref=sample.primary_source_ref,
        quality_profile="standard",
        target_vehicle_detected=observation.target_vehicle_present,
        target_vehicle_confidence=1.0 if observation.target_vehicle_present else 0.0,
        plate_candidate_detected=observation.plate_visible,
        plate_visibility_score=observation.plate_visibility_score,
        driver_risk_score=observation.risk_score,
        driver_risk_label=observation.risk_label,
        distance_meters=None,
        summary_message=observation.summary,
        notes=(
            "dataset=legacy_observed_media_bundle",
            f"sample_id={sample.sample_id}",
            f"video_path={sample.video_path}",
            f"screenshot_count={len(sample.screenshot_paths)}",
            "ground_truth=human_curated_clip_observations",
            *(event.label for event in observation.driver_events),
        ),
    )


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
