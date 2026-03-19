from __future__ import annotations

from dataclasses import dataclass

from ..integration import MockNumberVerificationGateway, MockQualityOnDemandGateway
from ..orchestration import (
    MockSessionRequest,
    MockTelecomOrchestrator,
    SceneAnalysisSummary,
)
from ..policy import QodPolicy, load_default_qod_policy
from ..qod import SceneSignal
from .models import (
    AnalysisResult,
    AnalysisSessionRequest,
    AnalysisSessionResult,
    AnalyzerInput,
    SceneAnalyzer,
)


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
    analysis_result = active_analyzer.analyze(request.analyzer_input)
    workflow_request = MockSessionRequest(
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
    orchestrator = MockTelecomOrchestrator(
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
