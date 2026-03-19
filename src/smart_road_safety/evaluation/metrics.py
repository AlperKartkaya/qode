from __future__ import annotations

from dataclasses import dataclass

from ..orchestration import MockSessionResult
from .models import ExpectedWorkflowOutcome


def _mean(values: tuple[float, ...]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


@dataclass(frozen=True)
class ScenarioMetricSummary:
    qod_selectivity_score: float
    policy_consistency_score: float
    placeholder_label_agreement_score: float
    all_expectations_met: bool


@dataclass(frozen=True)
class ScenarioSuiteSummary:
    scenario_count: int
    expectation_pass_count: int
    qod_request_rate: float
    qod_acceptance_rate: float
    average_qod_selectivity_score: float
    average_policy_consistency_score: float
    average_placeholder_label_agreement_score: float


def score_scenario(
    actual: MockSessionResult, expected: ExpectedWorkflowOutcome
) -> ScenarioMetricSummary:
    qod_selectivity_score = (
        1.0 if actual.mobile_view.qod_requested == expected.qod_requested else 0.0
    )

    policy_checks = (
        1.0 if actual.status == expected.status else 0.0,
        1.0 if actual.mobile_view.qod_requested == expected.qod_requested else 0.0,
        1.0 if actual.mobile_view.qod_accepted == expected.qod_accepted else 0.0,
        1.0 if actual.mobile_view.active_profile == expected.active_profile else 0.0,
    )
    policy_consistency_score = _mean(policy_checks)

    label_checks = (
        1.0
        if actual.mobile_view.target_vehicle_detected
        == expected.target_vehicle_detected
        else 0.0,
        1.0
        if actual.mobile_view.plate_candidate_detected
        == expected.plate_candidate_detected
        else 0.0,
        1.0
        if actual.mobile_view.driver_risk_label == expected.driver_risk_label
        else 0.0,
    )
    placeholder_label_agreement_score = _mean(label_checks)

    all_expectations_met = (
        qod_selectivity_score == 1.0
        and policy_consistency_score == 1.0
        and placeholder_label_agreement_score == 1.0
    )

    return ScenarioMetricSummary(
        qod_selectivity_score=qod_selectivity_score,
        policy_consistency_score=policy_consistency_score,
        placeholder_label_agreement_score=placeholder_label_agreement_score,
        all_expectations_met=all_expectations_met,
    )


def summarize_suite(entries: tuple["ScenarioReportEntry", ...]) -> ScenarioSuiteSummary:
    scenario_count = len(entries)
    expectation_pass_count = sum(
        1 for entry in entries if entry.metrics.all_expectations_met
    )
    qod_request_rate = _mean(
        tuple(
            1.0 if entry.actual.mobile_view.qod_requested else 0.0 for entry in entries
        )
    )
    qod_acceptance_rate = _mean(
        tuple(
            1.0 if entry.actual.mobile_view.qod_accepted else 0.0 for entry in entries
        )
    )
    average_qod_selectivity_score = _mean(
        tuple(entry.metrics.qod_selectivity_score for entry in entries)
    )
    average_policy_consistency_score = _mean(
        tuple(entry.metrics.policy_consistency_score for entry in entries)
    )
    average_placeholder_label_agreement_score = _mean(
        tuple(entry.metrics.placeholder_label_agreement_score for entry in entries)
    )

    return ScenarioSuiteSummary(
        scenario_count=scenario_count,
        expectation_pass_count=expectation_pass_count,
        qod_request_rate=qod_request_rate,
        qod_acceptance_rate=qod_acceptance_rate,
        average_qod_selectivity_score=average_qod_selectivity_score,
        average_policy_consistency_score=average_policy_consistency_score,
        average_placeholder_label_agreement_score=average_placeholder_label_agreement_score,
    )


from .models import ScenarioReportEntry  # noqa: E402
