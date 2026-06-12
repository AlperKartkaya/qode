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
            "The primary project data now consists of State Farm image frames, "
            "DMD video/OpenLABEL subsets, and DriverSVT CSV telemetry; the "
            "legacy three-video media bundle is secondary."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from data/datasets/* and data/real_dataset_manifest.json.",
        impact_surface=("ingestion", "batching", "preprocessing"),
    ),
    AssumptionRecord(
        assumption_id="DS-002",
        domain="sample unit",
        statement=(
            "Sample units vary by dataset: State Farm images, DMD video sessions, "
            "DriverSVT telemetry rows, and legacy video clips."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from manifests and dataset tree inspection.",
        impact_surface=("dataset adapters", "evaluation"),
    ),
    AssumptionRecord(
        assumption_id="DS-003",
        domain="annotation source",
        statement=(
            "Annotations come from State Farm folder/CSV labels, DMD OpenLABEL JSON, "
            "DriverSVT dangerousstate CSV labels, and the legacy clip observation registry."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from local label files and manifests.",
        impact_surface=("parsers", "schema validation", "evaluation"),
    ),
    AssumptionRecord(
        assumption_id="DS-004",
        domain="targets",
        statement=(
            "Driver-behavior monitoring is the primary target family; vehicle/plate "
            "detection is available only for the legacy observed media bundle."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from primary dataset labels.",
        impact_surface=("model heads", "UI output", "evaluation"),
    ),
    AssumptionRecord(
        assumption_id="DS-006",
        domain="speed labels",
        statement=(
            "DriverSVT provides numeric dataset-native speed telemetry; State Farm "
            "and DMD do not provide speed ground truth."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from DriverSVT.csv and absent unit docs.",
        impact_surface=("normalization", "reporting"),
    ),
    AssumptionRecord(
        assumption_id="DS-008",
        domain="annotation granularity",
        statement=(
            "Annotation granularity is per-image for State Farm, frame-level intervals "
            "for DMD, row-level states for DriverSVT, and clip-level observations for legacy media."
        ),
        confidence="high",
        verify_when_dataset_arrives="Verified from manifests and local annotation files.",
        impact_surface=("temporal logic", "metrics", "adapters"),
    ),
    AssumptionRecord(
        assumption_id="DS-009",
        domain="split strategy",
        statement=(
            "State Farm has labelled train subjects and an unlabeled official test set; "
            "DMD and DriverSVT require custom subject/user-grouped splits."
        ),
        confidence="high",
        verify_when_dataset_arrives="Update only if official competition splits are provided.",
        impact_surface=("experimentation", "evaluation"),
    ),
    AssumptionRecord(
        assumption_id="DS-012",
        domain="QoD policy",
        statement=(
            "QoD should be triggered only when higher network quality has an observable "
            "benefit for driver-risk or detailed in-cabin analysis."
        ),
        confidence="high",
        verify_when_dataset_arrives="Confirm against final API docs and judging guidance.",
        impact_surface=("network orchestration", "simulation"),
    ),
    AssumptionRecord(
        assumption_id="DS-014",
        domain="QoD API integration",
        statement=(
            "Real QoD endpoint details remain unavailable, so the repository keeps "
            "explicit mock-backed QoD activation behavior."
        ),
        confidence="high",
        verify_when_dataset_arrives="Update only if operator access is separately granted.",
        impact_surface=("API clients", "mobile flow", "backend integration"),
    ),
    AssumptionRecord(
        assumption_id="OR-002",
        domain="orchestration risk labels",
        statement=(
            "Mobile-facing risk labels are derived from the selected real dataset label "
            "or the legacy observation registry."
        ),
        confidence="high",
        verify_when_dataset_arrives="Update only if the project taxonomy intentionally changes.",
        impact_surface=("mobile output", "reporting", "evaluation"),
    ),
)
