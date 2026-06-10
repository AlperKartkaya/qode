from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..data import build_adapter_from_manifest_path
from ..integration import MockNumberVerificationGateway, MockQualityOnDemandGateway
from ..orchestration import (
    SceneAnalysisSummary,
    SessionRequest,
    TelecomOrchestrator,
)
from ..policy import QodPolicy, load_default_qod_policy
from ..qod import SceneSignal
from .models import (
    AnalysisResult,
    AnalysisSessionRequest,
    AnalysisSessionResult,
    AnalyzerInput,
    DatasetSelection,
    SceneAnalyzer,
)
from .observations import ObservationRegistry


@dataclass
class PlaceholderSceneAnalyzer(SceneAnalyzer):
    policy: QodPolicy | None = None

    def analyze(self, analyzer_input: AnalyzerInput) -> AnalysisResult:
        active_policy = (
            self.policy if self.policy is not None else load_default_qod_policy()
        )
        target_vehicle_detected = (
            analyzer_input.target_vehicle_confidence
            >= active_policy.togg_confidence_threshold
        )
        plate_candidate_detected = (
            analyzer_input.plate_visibility_score >= active_policy.plate_visibility_min
        )
        summary_message = self._build_summary_message(
            target_vehicle_detected=target_vehicle_detected,
            plate_candidate_detected=plate_candidate_detected,
            driver_risk_score=analyzer_input.driver_risk_score,
        )

        return AnalysisResult(
            source_ref=analyzer_input.source_ref,
            quality_profile=analyzer_input.quality_profile,
            target_vehicle_detected=target_vehicle_detected,
            target_vehicle_confidence=analyzer_input.target_vehicle_confidence,
            plate_candidate_detected=plate_candidate_detected,
            plate_visibility_score=analyzer_input.plate_visibility_score,
            driver_risk_score=analyzer_input.driver_risk_score,
            driver_risk_label=analyzer_input.driver_risk_label,
            distance_meters=analyzer_input.distance_meters,
            summary_message=summary_message,
            notes=analyzer_input.notes,
        )

    def _build_summary_message(
        self,
        target_vehicle_detected: bool,
        plate_candidate_detected: bool,
        driver_risk_score: float,
    ) -> str:
        states: list[str] = []
        if target_vehicle_detected:
            states.append("target vehicle signal present")
        if plate_candidate_detected:
            states.append("plate candidate signal present")
        if driver_risk_score > 0.0:
            states.append("driver risk score available")
        if not states:
            return "Placeholder analyzer produced no significant signals."
        return "Placeholder analyzer produced: " + ", ".join(states) + "."


def run_analysis_session(
    request: AnalysisSessionRequest,
    analyzer: SceneAnalyzer | None = None,
    policy: QodPolicy | None = None,
) -> AnalysisSessionResult:
    active_policy = policy if policy is not None else load_default_qod_policy()
    active_analyzer = (
        analyzer
        if analyzer is not None
        else PlaceholderSceneAnalyzer(policy=active_policy)
    )
    analysis_result = _build_analysis_result(
        request=request,
        analyzer=active_analyzer,
    )
    workflow_request = SessionRequest(
        session_id=request.session_id,
        phone_number=request.phone_number,
        device_session_id=request.device_session_id,
        requested_profile=request.requested_profile,
        scene_signal=SceneSignal(
            togg_candidate_confidence=analysis_result.target_vehicle_confidence,
            plate_visibility_score=analysis_result.plate_visibility_score,
            driver_risk_score=analysis_result.driver_risk_score,
            distance_meters=analysis_result.distance_meters,
            current_profile=analysis_result.quality_profile,
        ),
        analysis_summary=SceneAnalysisSummary(
            source_ref=analysis_result.source_ref,
            target_vehicle_detected=analysis_result.target_vehicle_detected,
            plate_candidate_detected=analysis_result.plate_candidate_detected,
            driver_risk_label=analysis_result.driver_risk_label,
            notes=(analysis_result.summary_message, *analysis_result.notes),
        ),
    )
    orchestrator = TelecomOrchestrator(
        number_verification_gateway=MockNumberVerificationGateway(
            verified_numbers=(request.phone_number,)
            if request.verification_should_pass
            else ()
        ),
        quality_on_demand_gateway=MockQualityOnDemandGateway(
            available_profiles=("standard", "boosted")
            if request.qod_should_allow_boost
            else ("standard",)
        ),
        policy=active_policy,
    )
    workflow_result = orchestrator.run(workflow_request)
    return AnalysisSessionResult(
        analysis_result=analysis_result,
        workflow_result=workflow_result,
    )


def _build_analysis_result(
    request: AnalysisSessionRequest,
    analyzer: SceneAnalyzer,
) -> AnalysisResult:
    if request.analyzer_input is not None:
        return analyzer.analyze(request.analyzer_input)

    if request.dataset_selection is None:
        raise ValueError(
            "AnalysisSessionRequest requires analyzer_input or dataset_selection."
        )

    return _build_dataset_backed_result(request.dataset_selection)


def _build_dataset_backed_result(dataset_selection: DatasetSelection) -> AnalysisResult:
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
            f"sample_id={sample.sample_id}",
            f"video_path={sample.video_path}",
            f"screenshot_count={len(sample.screenshot_paths)}",
            *(event.label for event in observation.driver_events),
        ),
    )
