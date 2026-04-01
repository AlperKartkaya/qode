from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..analysis import AnalysisSessionRequest
from ..orchestration import MockSessionRequest, MockSessionResult, OrchestrationEvent

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
class ScenarioGatewaySetup:
    verified_numbers: tuple[str, ...] = ()
    available_profiles: tuple[str, ...] = ("standard", "boosted")
    denied_session_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ScenarioGatewaySetup":
        return cls(
            verified_numbers=tuple(
                str(value) for value in payload.get("verified_numbers", [])
            ),
            available_profiles=tuple(
                str(value)
                for value in payload.get("available_profiles", ["standard", "boosted"])
            ),
            denied_session_ids=tuple(
                str(value) for value in payload.get("denied_session_ids", [])
            ),
        )


@dataclass(frozen=True)
class ExpectedWorkflowOutcome:
    status: str
    qod_requested: bool
    qod_accepted: bool
    active_profile: str
    target_vehicle_detected: bool
    plate_candidate_detected: bool
    driver_risk_label: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", _require_status(self.status))
        object.__setattr__(
            self,
            "active_profile",
            _require_text(self.active_profile, "active_profile"),
        )
        object.__setattr__(
            self,
            "driver_risk_label",
            _require_text(self.driver_risk_label, "driver_risk_label"),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExpectedWorkflowOutcome":
        required_keys = {
            "status",
            "qod_requested",
            "qod_accepted",
            "active_profile",
            "target_vehicle_detected",
            "plate_candidate_detected",
            "driver_risk_label",
        }
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(
                f"Expected workflow outcome is missing required keys: {', '.join(missing)}"
            )

        return cls(
            status=str(payload["status"]),
            qod_requested=bool(payload["qod_requested"]),
            qod_accepted=bool(payload["qod_accepted"]),
            active_profile=str(payload["active_profile"]),
            target_vehicle_detected=bool(payload["target_vehicle_detected"]),
            plate_candidate_detected=bool(payload["plate_candidate_detected"]),
            driver_risk_label=str(payload["driver_risk_label"]),
        )


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    description: str
    orchestration_request: MockSessionRequest | None
    analysis_session_request: AnalysisSessionRequest | None
    gateway_setup: ScenarioGatewaySetup
    expected: ExpectedWorkflowOutcome
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "scenario_id", _require_text(self.scenario_id, "scenario_id")
        )
        object.__setattr__(
            self,
            "description",
            _require_text(self.description, "description"),
        )
        if self.orchestration_request is None and self.analysis_session_request is None:
            raise ValueError(
                "ScenarioDefinition requires orchestration_request or analysis_session_request."
            )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ScenarioDefinition":
        required_keys = {
            "scenario_id",
            "description",
            "expected",
        }
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(
                f"Scenario definition is missing required keys: {', '.join(missing)}"
            )

        return cls(
            scenario_id=str(payload["scenario_id"]),
            description=str(payload["description"]),
            orchestration_request=None
            if payload.get("orchestration_request") is None
            else MockSessionRequest.from_dict(payload["orchestration_request"]),
            analysis_session_request=None
            if payload.get("analysis_session_request") is None
            else AnalysisSessionRequest.from_dict(payload["analysis_session_request"]),
            gateway_setup=ScenarioGatewaySetup.from_dict(
                payload.get("gateway_setup", {})
            ),
            expected=ExpectedWorkflowOutcome.from_dict(payload["expected"]),
            notes=tuple(str(value) for value in payload.get("notes", [])),
        )

    @classmethod
    def from_path(cls, file_path: str | Path) -> "ScenarioDefinition":
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)


@dataclass(frozen=True)
class ScenarioTraceBundle:
    scenario_id: str
    phases: tuple[str, ...]
    context_codes: tuple[str, ...]
    qod_reasons: tuple[str, ...]
    verification_reference: str
    qod_request_reference: str | None


@dataclass(frozen=True)
class ScenarioReportEntry:
    scenario_id: str
    description: str
    expected: ExpectedWorkflowOutcome
    actual: MockSessionResult
    trace: ScenarioTraceBundle
    metrics: "ScenarioMetricSummary"


@dataclass(frozen=True)
class ScenarioSuiteReport:
    report_version: str
    scenarios: tuple[ScenarioReportEntry, ...]
    summary: "ScenarioSuiteSummary"


def build_trace_bundle(
    scenario_id: str, result: MockSessionResult
) -> ScenarioTraceBundle:
    phases = tuple(event.phase for event in result.events)
    context_codes = tuple(event.context_code for event in result.events)
    qod_request_reference = None
    if result.qod_result is not None:
        qod_request_reference = result.qod_result.request_reference

    return ScenarioTraceBundle(
        scenario_id=scenario_id,
        phases=phases,
        context_codes=context_codes,
        qod_reasons=result.qod_decision.reasons,
        verification_reference=result.bootstrap_result.verification_reference,
        qod_request_reference=qod_request_reference,
    )


if TYPE_CHECKING:
    from .metrics import ScenarioMetricSummary, ScenarioSuiteSummary
