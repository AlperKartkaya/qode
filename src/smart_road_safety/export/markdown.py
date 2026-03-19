from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _format_ratio(value: float) -> str:
    return f"{value:.2f}"


def _bool_label(value: bool) -> str:
    return "yes" if value else "no"


def _load_report_payload(report_path: str | Path) -> dict[str, Any]:
    return json.loads(Path(report_path).read_text(encoding="utf-8"))


def render_scenario_report_markdown(report_path: str | Path) -> str:
    payload = _load_report_payload(report_path)
    summary = payload["summary"]
    scenarios = payload["scenarios"]
    lines: list[str] = []

    lines.append("# Scenario Evaluation Report")
    lines.append("")
    lines.append(f"Report version: `{payload['report_version']}`")
    lines.append("")
    lines.append("## Overall Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Scenario count | {summary['scenario_count']} |")
    lines.append(f"| Expectations met | {summary['expectation_pass_count']} |")
    lines.append(f"| QoD request rate | {_format_ratio(summary['qod_request_rate'])} |")
    lines.append(
        f"| QoD acceptance rate | {_format_ratio(summary['qod_acceptance_rate'])} |"
    )
    lines.append(
        f"| Avg QoD selectivity | {_format_ratio(summary['average_qod_selectivity_score'])} |"
    )
    lines.append(
        f"| Avg policy consistency | {_format_ratio(summary['average_policy_consistency_score'])} |"
    )
    lines.append(
        "| Avg placeholder label agreement | "
        f"{_format_ratio(summary['average_placeholder_label_agreement_score'])} |"
    )
    lines.append("")
    lines.append("## Scenario Table")
    lines.append("")
    lines.append(
        "| Scenario | Status | QoD requested | QoD accepted | Active profile | Expectations met |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- |")

    for scenario in scenarios:
        actual = scenario["actual"]
        mobile_view = actual["mobile_view"]
        metrics = scenario["metrics"]
        lines.append(
            "| "
            f"{scenario['scenario_id']} | {actual['status']} | {_bool_label(mobile_view['qod_requested'])} | "
            f"{_bool_label(mobile_view['qod_accepted'])} | {mobile_view['active_profile']} | "
            f"{_bool_label(metrics['all_expectations_met'])} |"
        )

    for scenario in scenarios:
        actual = scenario["actual"]
        mobile_view = actual["mobile_view"]
        trace = scenario["trace"]
        metrics = scenario["metrics"]
        lines.append("")
        lines.append(f"## Scenario: `{scenario['scenario_id']}`")
        lines.append("")
        lines.append(scenario["description"])
        lines.append("")
        lines.append("| Field | Expected | Actual |")
        lines.append("| --- | --- | --- |")
        lines.append(
            f"| Status | {scenario['expected']['status']} | {actual['status']} |"
        )
        lines.append(
            "| QoD requested | "
            f"{_bool_label(scenario['expected']['qod_requested'])} | {_bool_label(mobile_view['qod_requested'])} |"
        )
        lines.append(
            "| QoD accepted | "
            f"{_bool_label(scenario['expected']['qod_accepted'])} | {_bool_label(mobile_view['qod_accepted'])} |"
        )
        lines.append(
            f"| Active profile | {scenario['expected']['active_profile']} | {mobile_view['active_profile']} |"
        )
        lines.append(
            f"| Driver risk label | {scenario['expected']['driver_risk_label']} | {mobile_view['driver_risk_label']} |"
        )
        lines.append("")
        lines.append("Trace phases: " + " -> ".join(trace["phases"]))
        lines.append("")
        lines.append("Trace context codes:")
        lines.append("")
        for context_code in trace["context_codes"]:
            lines.append(f"- `{context_code}`")
        if trace["qod_reasons"]:
            lines.append("")
            lines.append("QoD rationale:")
            lines.append("")
            for reason in trace["qod_reasons"]:
                lines.append(f"- {reason}")
        lines.append("")
        lines.append(
            "Metric snapshot: "
            f"selectivity={_format_ratio(metrics['qod_selectivity_score'])}, "
            f"policy={_format_ratio(metrics['policy_consistency_score'])}, "
            f"labels={_format_ratio(metrics['placeholder_label_agreement_score'])}"
        )

    lines.append("")
    return "\n".join(lines)


def export_scenario_report_markdown(
    report_path: str | Path, output_path: str | Path
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_scenario_report_markdown(report_path), encoding="utf-8")
    return target
