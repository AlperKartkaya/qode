from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..analysis import run_analysis_session
from ..integration import MockNumberVerificationGateway, MockQualityOnDemandGateway
from ..orchestration import TelecomOrchestrator
from ..policy import QodPolicy, load_default_qod_policy
from .metrics import score_scenario, summarize_suite
from .models import (
    ScenarioDefinition,
    ScenarioReportEntry,
    ScenarioSuiteReport,
    build_trace_bundle,
)


def _load_scenarios(path: str | Path) -> tuple[ScenarioDefinition, ...]:
    target = Path(path)
    if target.is_file():
        return (ScenarioDefinition.from_path(target),)
    if target.is_dir():
        scenario_files = sorted(target.glob("*.json"))
        return tuple(
            ScenarioDefinition.from_path(file_path) for file_path in scenario_files
        )
    raise ValueError(f"Scenario path does not exist: {target}")


def run_scenario_suite(
    scenario_path: str | Path,
    output_path: str | Path | None = None,
    policy: QodPolicy | None = None,
) -> ScenarioSuiteReport:
    active_policy = policy if policy is not None else load_default_qod_policy()
    scenarios = _load_scenarios(scenario_path)
    entries: list[ScenarioReportEntry] = []

    for scenario in scenarios:
        if scenario.analysis_session_request is not None:
            actual = run_analysis_session(
                request=scenario.analysis_session_request,
                policy=active_policy,
            ).workflow_result
        else:
            if scenario.orchestration_request is None:
                raise ValueError(
                    f"Scenario {scenario.scenario_id} has no executable request payload."
                )
            orchestrator = TelecomOrchestrator(
                number_verification_gateway=MockNumberVerificationGateway(
                    verified_numbers=scenario.gateway_setup.verified_numbers
                ),
                quality_on_demand_gateway=MockQualityOnDemandGateway(
                    available_profiles=scenario.gateway_setup.available_profiles,
                    denied_session_ids=scenario.gateway_setup.denied_session_ids,
                ),
                policy=active_policy,
            )
            actual = orchestrator.run(scenario.orchestration_request)
        metrics = score_scenario(actual=actual, expected=scenario.expected)
        trace = build_trace_bundle(scenario_id=scenario.scenario_id, result=actual)
        entries.append(
            ScenarioReportEntry(
                scenario_id=scenario.scenario_id,
                description=scenario.description,
                expected=scenario.expected,
                actual=actual,
                trace=trace,
                metrics=metrics,
            )
        )

    report = ScenarioSuiteReport(
        report_version="scenario-to-score-v1",
        scenarios=tuple(entries),
        summary=summarize_suite(tuple(entries)),
    )

    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")

    return report
