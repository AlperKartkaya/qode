from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .analysis import AnalysisSessionRequest, run_analysis_session
from .assumptions import ASSUMPTIONS
from .competition import (
    VehicleInfo,
    build_ftr_result_from_analysis,
    read_ftr_result,
    write_ftr_result,
)
from .data import build_adapter_from_manifest_path
from .evaluation import run_scenario_suite
from .export import export_scenario_report_markdown
from .integration import (
    MockNumberVerificationGateway,
    MockQualityOnDemandGateway,
    build_qod_activation_request,
)
from .local_api import run_local_api_server
from .manifest import DatasetManifest, compare_manifest_to_assumptions
from .orchestration import SessionRequest, TelecomOrchestrator
from .policy import QodPolicy, load_default_qod_policy
from .qod import SceneSignal, evaluate_qod_need


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dataset-backed and FTR-aware utilities for the smart road safety project."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "print-assumptions", help="Print the current coded assumption registry."
    )

    check_manifest = subparsers.add_parser(
        "check-manifest", help="Check a dataset manifest against current assumptions."
    )
    check_manifest.add_argument(
        "manifest_path", help="Path to a dataset manifest JSON file."
    )

    plan_ingestion = subparsers.add_parser(
        "plan-ingestion",
        help="Resolve the current manifest to a dataset-adapter slot and print its ingestion plan.",
    )
    plan_ingestion.add_argument(
        "manifest_path", help="Path to a dataset manifest JSON file."
    )
    plan_ingestion.add_argument(
        "--dataset-root",
        default=None,
        help="Optional dataset root path for the adapter inventory and ingestion plan.",
    )

    inspect_dataset = subparsers.add_parser(
        "inspect-dataset",
        help="Load the current dataset inventory from a manifest and dataset root.",
    )
    inspect_dataset.add_argument(
        "manifest_path", help="Path to a dataset manifest JSON file."
    )
    inspect_dataset.add_argument(
        "--dataset-root",
        required=True,
        help="Path to the dataset root to inspect.",
    )

    subparsers.add_parser(
        "print-default-qod-policy",
        help="Print the packaged default QoD policy JSON.",
    )

    simulate_qod = subparsers.add_parser(
        "simulate-qod", help="Simulate a QoD decision from a scene signal JSON file."
    )
    simulate_qod.add_argument("scenario_path", help="Path to a QoD scenario JSON file.")
    simulate_qod.add_argument(
        "--policy-path",
        default=None,
        help="Optional QoD policy JSON file. If omitted, the packaged default is used.",
    )

    run_orchestration = subparsers.add_parser(
        "run-mock-orchestration",
        help=(
            "Run the support/demo session bootstrap and QoD orchestration flow "
            "with isolated mock telecom gateways."
        ),
    )
    run_orchestration.add_argument(
        "request_path",
        help="Path to a mock orchestration request JSON file.",
    )
    run_orchestration.add_argument(
        "--policy-path",
        default=None,
        help="Optional QoD policy JSON file. If omitted, the packaged default is used.",
    )

    run_analysis_session_parser = subparsers.add_parser(
        "run-analysis-session",
        help=(
            "Run the internal support/demo analysis session. "
            "Use build-ftr-output for the source-of-truth competition JSON."
        ),
    )
    run_analysis_session_parser.add_argument(
        "request_path",
        help="Path to an analysis session request JSON file.",
    )
    run_analysis_session_parser.add_argument(
        "--policy-path",
        default=None,
        help="Optional QoD policy JSON file. If omitted, the packaged default is used.",
    )

    build_ftr_output = subparsers.add_parser(
        "build-ftr-output",
        help=(
            "Run an analysis session and write the FTR/KTR results.json schema. "
            "Requires explicit vehicle info because support datasets do not carry "
            "exact plate/type/color labels."
        ),
    )
    build_ftr_output.add_argument(
        "request_path",
        help="Path to an analysis session request JSON file.",
    )
    build_ftr_output.add_argument(
        "--vehicle-info-path",
        required=True,
        help="JSON file with tip, plaka, renk, confidence_score.",
    )
    build_ftr_output.add_argument(
        "--video-id",
        required=True,
        help="Video id/name to emit in FTR results.json.",
    )
    build_ftr_output.add_argument(
        "--output-path",
        default="out/results.json",
        help="Path where FTR results JSON will be written.",
    )
    build_ftr_output.add_argument(
        "--event-time-seconds",
        type=float,
        default=0.0,
        help="Timestamp to assign to analysis-derived detection events.",
    )
    build_ftr_output.add_argument(
        "--policy-path",
        default=None,
        help="Optional QoD policy JSON file. If omitted, the packaged default is used.",
    )

    validate_ftr_output = subparsers.add_parser(
        "validate-ftr-output",
        help="Validate an FTR/KTR results.json file against the source-of-truth schema.",
    )
    validate_ftr_output.add_argument(
        "result_path",
        help="Path to a results.json file.",
    )

    run_scenarios = subparsers.add_parser(
        "run-scenarios",
        help=(
            "Run support/demo QoD scenarios. "
            "This is not the final FTR evaluator contract."
        ),
    )
    run_scenarios.add_argument(
        "scenario_path",
        help="Path to a scenario JSON file or a directory of scenario JSON files.",
    )
    run_scenarios.add_argument(
        "--output-path",
        default="out/scenario_report.json",
        help="Path where the scenario report JSON will be written.",
    )
    run_scenarios.add_argument(
        "--policy-path",
        default=None,
        help="Optional QoD policy JSON file. If omitted, the packaged default is used.",
    )

    export_report = subparsers.add_parser(
        "export-scenario-report",
        help=(
            "Render markdown from a support/demo scenario report JSON file. "
            "KTR/FTR report content is planned in docs/ktr_implementation_plan.md."
        ),
    )
    export_report.add_argument(
        "report_path",
        help="Path to a scenario report JSON file.",
    )
    export_report.add_argument(
        "--output-path",
        default="out/scenario_report.md",
        help="Path where the markdown export will be written.",
    )

    serve_local_api = subparsers.add_parser(
        "serve-local-api",
        help=(
            "Start a tiny local HTTP API exposing FTR endpoints plus support/demo "
            "orchestration and evaluation routes."
        ),
    )
    serve_local_api.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind.",
    )
    serve_local_api.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind.",
    )

    return parser


def _print_assumptions() -> int:
    for assumption in ASSUMPTIONS:
        print(
            f"{assumption.assumption_id} [{assumption.confidence}] {assumption.statement}"
        )
        print(f"  verify: {assumption.verify_when_dataset_arrives}")
        print(f"  impact: {', '.join(assumption.impact_surface)}")
    return 0


def _check_manifest(manifest_path: str) -> int:
    manifest = DatasetManifest.from_path(manifest_path)
    gaps = compare_manifest_to_assumptions(manifest)

    print(f"sample_unit={manifest.sample_unit}")
    print(f"targets={', '.join(manifest.targets)}")
    print(f"annotation_format={manifest.annotation_format}")

    if not gaps:
        print("result=pass")
        return 0

    print("result=adaptation-needed")
    for gap in gaps:
        print(f"- {gap.assumption_id} [{gap.severity}] {gap.message}")
        print(f"  action: {gap.action}")
    return 0


def _plan_ingestion(manifest_path: str, dataset_root: str | None) -> int:
    adapter = build_adapter_from_manifest_path(
        manifest_path=manifest_path,
        dataset_root=dataset_root,
    )
    plan = adapter.build_ingestion_plan()
    print(json.dumps(asdict(plan), indent=2))
    return 0


def _inspect_dataset(manifest_path: str, dataset_root: str) -> int:
    adapter = build_adapter_from_manifest_path(
        manifest_path=manifest_path,
        dataset_root=dataset_root,
    )
    inventory = adapter.load_inventory()
    print(json.dumps(asdict(inventory), indent=2))
    return 0


def _print_default_qod_policy() -> int:
    policy = load_default_qod_policy()
    print(json.dumps(policy.to_dict(), indent=2))
    return 0


def _simulate_qod(scenario_path: str, policy_path: str | None) -> int:
    signal = SceneSignal.from_path(scenario_path)
    policy = (
        load_default_qod_policy()
        if policy_path is None
        else QodPolicy.from_path(policy_path)
    )
    decision = evaluate_qod_need(signal, policy=policy)
    qod_request = build_qod_activation_request(
        session_id="demo-session", decision=decision, policy=policy
    )
    print(
        json.dumps(
            {
                "policy": policy.to_dict(),
                "decision": asdict(decision),
                "qod_request": None if qod_request is None else asdict(qod_request),
            },
            indent=2,
        )
    )
    return 0


def _run_mock_orchestration(request_path: str, policy_path: str | None) -> int:
    policy = (
        load_default_qod_policy()
        if policy_path is None
        else QodPolicy.from_path(policy_path)
    )
    request = SessionRequest.from_path(request_path)
    orchestrator = TelecomOrchestrator(
        number_verification_gateway=MockNumberVerificationGateway(
            verified_numbers=(request.phone_number,)
        ),
        quality_on_demand_gateway=MockQualityOnDemandGateway(),
        policy=policy,
    )
    result = orchestrator.run(request)
    print(json.dumps(asdict(result), indent=2))
    return 0


def _run_analysis_session(request_path: str, policy_path: str | None) -> int:
    policy = (
        load_default_qod_policy()
        if policy_path is None
        else QodPolicy.from_path(policy_path)
    )
    request = AnalysisSessionRequest.from_path(request_path)
    result = run_analysis_session(request=request, policy=policy)
    print(json.dumps(asdict(result), indent=2))
    return 0


def _build_ftr_output(
    request_path: str,
    vehicle_info_path: str,
    video_id: str,
    output_path: str,
    event_time_seconds: float,
    policy_path: str | None,
) -> int:
    policy = (
        load_default_qod_policy()
        if policy_path is None
        else QodPolicy.from_path(policy_path)
    )
    request = AnalysisSessionRequest.from_path(request_path)
    session_result = run_analysis_session(request=request, policy=policy)
    vehicle_payload = json.loads(Path(vehicle_info_path).read_text(encoding="utf-8"))
    vehicle_info = VehicleInfo.from_dict(vehicle_payload)
    ftr_result = build_ftr_result_from_analysis(
        analysis_result=session_result.analysis_result,
        video_id=video_id,
        vehicle_info=vehicle_info,
        event_time_seconds=event_time_seconds,
    )
    target = write_ftr_result(ftr_result, output_path)
    print(f"results_path={target}")
    print(json.dumps(ftr_result.to_dict(), indent=2))
    return 0


def _validate_ftr_output(result_path: str) -> int:
    result = read_ftr_result(result_path)
    print("result=pass")
    print(f"video_id={result.video_id}")
    print(f"tespit_count={len(result.tespitler)}")
    return 0


def _run_scenarios(
    scenario_path: str, output_path: str, policy_path: str | None
) -> int:
    policy = (
        load_default_qod_policy()
        if policy_path is None
        else QodPolicy.from_path(policy_path)
    )
    report = run_scenario_suite(
        scenario_path=scenario_path,
        output_path=output_path,
        policy=policy,
    )
    print(f"report_path={Path(output_path)}")
    print(json.dumps(asdict(report.summary), indent=2))
    return 0


def _export_scenario_report(report_path: str, output_path: str) -> int:
    target = export_scenario_report_markdown(
        report_path=report_path,
        output_path=output_path,
    )
    print(f"markdown_path={target}")
    return 0


def _serve_local_api(host: str, port: int) -> int:
    run_local_api_server(host=host, port=port)
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "print-assumptions":
        return _print_assumptions()
    if args.command == "check-manifest":
        return _check_manifest(args.manifest_path)
    if args.command == "plan-ingestion":
        return _plan_ingestion(args.manifest_path, args.dataset_root)
    if args.command == "inspect-dataset":
        return _inspect_dataset(args.manifest_path, args.dataset_root)
    if args.command == "print-default-qod-policy":
        return _print_default_qod_policy()
    if args.command == "simulate-qod":
        return _simulate_qod(args.scenario_path, args.policy_path)
    if args.command == "run-mock-orchestration":
        return _run_mock_orchestration(args.request_path, args.policy_path)
    if args.command == "run-analysis-session":
        return _run_analysis_session(args.request_path, args.policy_path)
    if args.command == "build-ftr-output":
        return _build_ftr_output(
            args.request_path,
            args.vehicle_info_path,
            args.video_id,
            args.output_path,
            args.event_time_seconds,
            args.policy_path,
        )
    if args.command == "validate-ftr-output":
        return _validate_ftr_output(args.result_path)
    if args.command == "run-scenarios":
        return _run_scenarios(args.scenario_path, args.output_path, args.policy_path)
    if args.command == "export-scenario-report":
        return _export_scenario_report(args.report_path, args.output_path)
    if args.command == "serve-local-api":
        return _serve_local_api(args.host, args.port)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
