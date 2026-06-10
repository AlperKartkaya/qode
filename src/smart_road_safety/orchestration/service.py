from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..integration import (
    MobileSessionBootstrapRequest,
    MobileSessionBootstrapResult,
    NumberVerificationGateway,
    NumberVerificationRequest,
    QodActivationRequest,
    QodActivationResult,
    QualityOnDemandGateway,
    build_qod_activation_request,
)
from ..policy import QodPolicy, load_default_qod_policy
from ..qod import QodDecision, SceneSignal, evaluate_qod_need

WORKFLOW_STATUSES = {"SUCCESS", "PARTIAL", "FAILED"}


def _require_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty.")
    return cleaned


def _require_status(value: str) -> str:
    status = _require_text(value, "status")
    if status not in WORKFLOW_STATUSES:
        raise ValueError(f"Unsupported workflow status: {status}")
    return status


@dataclass(frozen=True)
class SceneAnalysisSummary:
    source_ref: str
    target_vehicle_detected: bool
    plate_candidate_detected: bool
    driver_risk_label: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_ref", _require_text(self.source_ref, "source_ref")
        )
        object.__setattr__(
            self,
            "driver_risk_label",
            _require_text(self.driver_risk_label, "driver_risk_label"),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SceneAnalysisSummary":
        required_keys = {
            "source_ref",
            "target_vehicle_detected",
            "plate_candidate_detected",
            "driver_risk_label",
        }
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(
                f"Scene analysis summary is missing required keys: {', '.join(missing)}"
            )

        return cls(
            source_ref=str(payload["source_ref"]),
            target_vehicle_detected=bool(payload["target_vehicle_detected"]),
            plate_candidate_detected=bool(payload["plate_candidate_detected"]),
            driver_risk_label=str(payload["driver_risk_label"]),
            notes=tuple(str(value) for value in payload.get("notes", [])),
        )


@dataclass(frozen=True)
class SessionRequest:
    session_id: str
    phone_number: str
    device_session_id: str
    requested_profile: str
    scene_signal: SceneSignal
    analysis_summary: SceneAnalysisSummary

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "session_id", _require_text(self.session_id, "session_id")
        )
        object.__setattr__(
            self, "phone_number", _require_text(self.phone_number, "phone_number")
        )
        object.__setattr__(
            self,
            "device_session_id",
            _require_text(self.device_session_id, "device_session_id"),
        )
        object.__setattr__(
            self,
            "requested_profile",
            _require_text(self.requested_profile, "requested_profile"),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionRequest":
        required_keys = {
            "session_id",
            "phone_number",
            "device_session_id",
            "requested_profile",
            "scene_signal",
            "analysis_summary",
        }
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(
                f"Session request is missing required keys: {', '.join(missing)}"
            )

        scene_signal = SceneSignal(
            togg_candidate_confidence=float(
                payload["scene_signal"]["togg_candidate_confidence"]
            ),
            plate_visibility_score=float(
                payload["scene_signal"]["plate_visibility_score"]
            ),
            driver_risk_score=float(payload["scene_signal"]["driver_risk_score"]),
            distance_meters=None
            if payload["scene_signal"]["distance_meters"] is None
            else float(payload["scene_signal"]["distance_meters"]),
            current_profile=str(
                payload["scene_signal"].get("current_profile", "standard")
            ),
        )

        return cls(
            session_id=str(payload["session_id"]),
            phone_number=str(payload["phone_number"]),
            device_session_id=str(payload["device_session_id"]),
            requested_profile=str(payload["requested_profile"]),
            scene_signal=scene_signal,
            analysis_summary=SceneAnalysisSummary.from_dict(
                payload["analysis_summary"]
            ),
        )

    @classmethod
    def from_path(cls, file_path: str | Path) -> "SessionRequest":
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)


@dataclass(frozen=True)
class OrchestrationEvent:
    phase: str
    context_code: str
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase", _require_text(self.phase, "phase"))
        object.__setattr__(
            self, "context_code", _require_text(self.context_code, "context_code")
        )
        object.__setattr__(self, "message", _require_text(self.message, "message"))


@dataclass(frozen=True)
class MobileWorkflowView:
    session_id: str
    status: str
    verification_passed: bool
    active_profile: str
    qod_requested: bool
    qod_accepted: bool
    source_ref: str
    target_vehicle_detected: bool
    plate_candidate_detected: bool
    driver_risk_label: str
    summary_message: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "session_id", _require_text(self.session_id, "session_id")
        )
        object.__setattr__(self, "status", _require_status(self.status))
        object.__setattr__(
            self, "active_profile", _require_text(self.active_profile, "active_profile")
        )
        object.__setattr__(
            self, "source_ref", _require_text(self.source_ref, "source_ref")
        )
        object.__setattr__(
            self,
            "driver_risk_label",
            _require_text(self.driver_risk_label, "driver_risk_label"),
        )
        object.__setattr__(
            self,
            "summary_message",
            _require_text(self.summary_message, "summary_message"),
        )


@dataclass(frozen=True)
class SessionResult:
    status: str
    bootstrap_result: MobileSessionBootstrapResult
    qod_decision: QodDecision
    qod_request: QodActivationRequest | None
    qod_result: QodActivationResult | None
    mobile_view: MobileWorkflowView
    events: tuple[OrchestrationEvent, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", _require_status(self.status))


class TelecomOrchestrator:
    def __init__(
        self,
        number_verification_gateway: NumberVerificationGateway,
        quality_on_demand_gateway: QualityOnDemandGateway,
        policy: QodPolicy | None = None,
    ) -> None:
        self._number_verification_gateway = number_verification_gateway
        self._quality_on_demand_gateway = quality_on_demand_gateway
        self._policy = policy if policy is not None else load_default_qod_policy()

    def run(self, request: SessionRequest) -> SessionResult:
        bootstrap_request = MobileSessionBootstrapRequest(
            phone_number=request.phone_number,
            device_session_id=request.device_session_id,
            requested_profile=request.requested_profile,
        )
        events = [
            OrchestrationEvent(
                phase="BOOTSTRAP_REQUESTED",
                context_code="SESSION.BOOTSTRAP_REQUESTED",
                message=(
                    f"Session bootstrap started for {bootstrap_request.device_session_id}"
                ),
            )
        ]

        verification_result = self._number_verification_gateway.verify_number(
            NumberVerificationRequest(
                phone_number=bootstrap_request.phone_number,
                device_session_id=bootstrap_request.device_session_id,
            )
        )
        bootstrap_result = MobileSessionBootstrapResult(
            session_id=request.session_id,
            verified=verification_result.verified,
            active_profile=bootstrap_request.requested_profile,
            verification_reference=verification_result.verification_reference,
            message=verification_result.reason or "NUMBER_VERIFICATION.UNKNOWN",
        )

        if not verification_result.verified:
            events.append(
                OrchestrationEvent(
                    phase="VERIFICATION_FAILED",
                    context_code="NUMBER_VERIFICATION.VERIFICATION_FAILED",
                    message="Silent number verification failed before QoD evaluation.",
                )
            )
            decision = QodDecision(
                should_activate=False,
                requested_profile=bootstrap_result.active_profile,
                reasons=("verification failed",),
                expected_benefit="No QoD request is attempted when verification fails.",
            )
            mobile_view = MobileWorkflowView(
                session_id=request.session_id,
                status="FAILED",
                verification_passed=False,
                active_profile=bootstrap_result.active_profile,
                qod_requested=False,
                qod_accepted=False,
                source_ref=request.analysis_summary.source_ref,
                target_vehicle_detected=request.analysis_summary.target_vehicle_detected,
                plate_candidate_detected=request.analysis_summary.plate_candidate_detected,
                driver_risk_label=request.analysis_summary.driver_risk_label,
                summary_message="Verification failed, so the workflow stopped before QoD.",
            )
            return SessionResult(
                status="FAILED",
                bootstrap_result=bootstrap_result,
                qod_decision=decision,
                qod_request=None,
                qod_result=None,
                mobile_view=mobile_view,
                events=tuple(events),
            )

        events.append(
            OrchestrationEvent(
                phase="NUMBER_VERIFIED",
                context_code="NUMBER_VERIFICATION.SUCCESS",
                message="Silent number verification passed.",
            )
        )

        decision = evaluate_qod_need(request.scene_signal, policy=self._policy)
        events.append(
            OrchestrationEvent(
                phase="QOD_EVALUATED",
                context_code="QOD.REQUEST_REQUIRED"
                if decision.should_activate
                else "QOD.NOT_REQUIRED",
                message=decision.expected_benefit,
            )
        )

        qod_request = build_qod_activation_request(
            session_id=request.session_id,
            decision=decision,
            policy=self._policy,
        )
        qod_result: QodActivationResult | None = None
        status = "SUCCESS"
        active_profile = bootstrap_result.active_profile
        summary_message = "Workflow completed without a QoD escalation request."

        if qod_request is not None:
            qod_result = self._quality_on_demand_gateway.activate_quality(qod_request)
            active_profile = (
                qod_result.applied_profile
                if qod_result.accepted
                else bootstrap_result.active_profile
            )
            if qod_result.accepted:
                events.append(
                    OrchestrationEvent(
                        phase="QOD_ACTIVATED",
                        context_code="QOD.ACTIVATED",
                        message="QoD request accepted by the mock gateway.",
                    )
                )
                summary_message = "Workflow completed with boosted network quality."
            else:
                events.append(
                    OrchestrationEvent(
                        phase="QOD_DENIED",
                        context_code=qod_result.denial_reason or "QOD.DENIED",
                        message="QoD request was denied by the mock gateway.",
                    )
                )
                status = "PARTIAL"
                summary_message = "Workflow completed, but QoD escalation was denied."

        mobile_view = MobileWorkflowView(
            session_id=request.session_id,
            status=status,
            verification_passed=True,
            active_profile=active_profile,
            qod_requested=qod_request is not None,
            qod_accepted=bool(qod_result and qod_result.accepted),
            source_ref=request.analysis_summary.source_ref,
            target_vehicle_detected=request.analysis_summary.target_vehicle_detected,
            plate_candidate_detected=request.analysis_summary.plate_candidate_detected,
            driver_risk_label=request.analysis_summary.driver_risk_label,
            summary_message=summary_message,
        )

        return SessionResult(
            status=status,
            bootstrap_result=bootstrap_result,
            qod_decision=decision,
            qod_request=qod_request,
            qod_result=qod_result,
            mobile_view=mobile_view,
            events=tuple(events),
        )
