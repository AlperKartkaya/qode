from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .assumptions import ASSUMPTIONS
from .data import build_adapter_from_manifest_path
from .integration import build_qod_activation_request
from .manifest import DatasetManifest, compare_manifest_to_assumptions
from .policy import QodPolicy, load_default_qod_policy
from .qod import SceneSignal, evaluate_qod_need


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pre-dataset utilities for the smart road safety project."
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
        help="Optional dataset root path for the future concrete adapter.",
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


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "print-assumptions":
        return _print_assumptions()
    if args.command == "check-manifest":
        return _check_manifest(args.manifest_path)
    if args.command == "plan-ingestion":
        return _plan_ingestion(args.manifest_path, args.dataset_root)
    if args.command == "print-default-qod-policy":
        return _print_default_qod_policy()
    if args.command == "simulate-qod":
        return _simulate_qod(args.scenario_path, args.policy_path)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
