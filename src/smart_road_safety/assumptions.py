from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssumptionRecord:
    assumption_id: str
    domain: str
    statement: str
    confidence: str
    verify_when_dataset_arrives: str
    impact_surface: tuple[str, ...]


ASSUMPTIONS: tuple[AssumptionRecord, ...] = (
    AssumptionRecord(
        assumption_id="DS-001",
        domain="dataset packaging",
        statement=(
            "Support datasets are State Farm images, DMD videos/OpenLABEL, "
            "DriverSVT telemetry, and the legacy three-video TOGG-like bundle; "
            "the final evaluator runs on organizer-provided videos."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from FTR and 2026 şartname source documents.",
        impact_surface=("ingestion", "preprocessing", "report wording"),
    ),
    AssumptionRecord(
        assumption_id="DS-002",
        domain="sample unit",
        statement=(
            "Support sample units vary by dataset, but final FTR inference sample "
            "unit is one video at /app/data/input/video.mp4."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from FTR Docker contract.",
        impact_surface=("dataset adapters", "submission wrapper"),
    ),
    AssumptionRecord(
        assumption_id="DS-003",
        domain="annotation source",
        statement=(
            "Support annotations keep their native labels, but final output must be "
            "the exact FTR results.json schema with ASCII-safe labels."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from FTR output examples.",
        impact_surface=("parsers", "schema validation", "competition exporter"),
    ),
    AssumptionRecord(
        assumption_id="DS-004",
        domain="targets",
        statement=(
            "The competition target taxonomy includes vehicle body type, plate, "
            "vehicle color, driver actions, selected objects, and passenger positions."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from FTR expected values and 2026 şartname target list.",
        impact_surface=("model heads", "output schema", "evaluation", "KTR report"),
    ),
    AssumptionRecord(
        assumption_id="DS-005",
        domain="plate labels",
        statement=(
            "Plate OCR is required for FTR output; current local support datasets do "
            "not provide reusable exact Turkish plate text labels."
        ),
        confidence="high",
        verify_when_dataset_arrives="Update only if organizer publishes labelled plate ground truth.",
        impact_surface=("OCR pipeline", "post-processing", "output validation"),
    ),
    AssumptionRecord(
        assumption_id="DS-006",
        domain="speed labels",
        statement=(
            "The şartname mentions real vehicle speed, but the current FTR results.json "
            "schema omits a speed key; keep speed as an internal/reporting objective until updated."
        ),
        confidence="medium",
        verify_when_dataset_arrives="Re-check if final KTR/FTR guidance revises results.json.",
        impact_surface=("normalization", "reporting", "optional model head"),
    ),
    AssumptionRecord(
        assumption_id="DS-007",
        domain="in-cabin labels",
        statement=(
            "FTR requires exact labels for driver actions, teknocan/bilgisayar, "
            "and passenger-seat positions; existing datasets cover only a subset."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from FTR labels and current manifests.",
        impact_surface=("classification schema", "dataset gap analysis"),
    ),
    AssumptionRecord(
        assumption_id="DS-008",
        domain="annotation granularity",
        statement=(
            "Support granularity varies, while final output is event-level with "
            "zaman_saniye plus one per-video arac_bilgisi summary."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from FTR output examples.",
        impact_surface=("temporal logic", "metrics", "adapter outputs"),
    ),
    AssumptionRecord(
        assumption_id="DS-010",
        domain="TOGG trigger",
        statement=(
            "TOGG/target-vehicle approach is a primary competition trigger for QoD; "
            "driver-behavior-only datasets are insufficient for the full yarışma scope."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from şartname purpose and QoD scenario wording.",
        impact_surface=("trigger policy", "detection logic", "model roadmap"),
    ),
    AssumptionRecord(
        assumption_id="DS-012",
        domain="QoD policy",
        statement=(
            "QoD should be requested only when TOGG approach, plate readability, "
            "driver-risk, or in-cabin detail creates observable benefit."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from şartname QoD scoring description; calibrate live later.",
        impact_surface=("network orchestration", "simulation", "report"),
    ),
    AssumptionRecord(
        assumption_id="DS-013",
        domain="Number Verification integration",
        statement=(
            "Real credentials are unavailable; mocks remain isolated while design "
            "tracks CAMARA/Open Gateway silent SIM/phone verification semantics."
        ),
        confidence="high",
        verify_when_dataset_arrives="Update when Turkcell credentials/base URL/device details are granted.",
        impact_surface=("mobile/auth integration",),
    ),
    AssumptionRecord(
        assumption_id="DS-014",
        domain="QoD API integration",
        statement=(
            "Real credentials are unavailable; mocks remain isolated while design "
            "tracks CAMARA/Open Gateway temporary QoS-session semantics."
        ),
        confidence="high",
        verify_when_dataset_arrives="Update when Turkcell credentials/base URL/QoS profile names are granted.",
        impact_surface=("API client", "orchestration"),
    ),
    AssumptionRecord(
        assumption_id="OR-002",
        domain="orchestration risk labels",
        statement=(
            "Internal labels may remain richer, but competition export must map to "
            "the exact FTR label set and reject unmapped labels."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from FTR exact-match warning.",
        impact_surface=("mobile output", "reporting", "evaluation"),
    ),
    AssumptionRecord(
        assumption_id="AN-002",
        domain="analyzer outputs",
        statement=(
            "The internal AnalysisResult remains useful for orchestration, but a "
            "separate FTR competition output contract is required for results.json."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from FTR schema mismatch.",
        impact_surface=("orchestration integration", "local API", "CLI"),
    ),
)
