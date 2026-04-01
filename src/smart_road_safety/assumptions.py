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
        statement="The final dataset is a mixed media bundle with MP4 videos and companion screenshots.",
        confidence="high",
        verify_when_dataset_arrives="Verified from the delivered data/ tree.",
        impact_surface=("ingestion", "batching", "preprocessing"),
    ),
    AssumptionRecord(
        assumption_id="DS-002",
        domain="sample unit",
        statement="The practical unit is one video clip plus its companion screenshots and clip-level observations.",
        confidence="high",
        verify_when_dataset_arrives="Verified from video_1..video_3, snap_from_video_* folders, and data/video_observations.json.",
        impact_surface=("dataset adapters", "evaluation"),
    ),
    AssumptionRecord(
        assumption_id="DS-003",
        domain="annotation source",
        statement="The final project uses a repository-local human-curated clip observation registry because no official structured sidecar annotations were delivered.",
        confidence="high",
        verify_when_dataset_arrives="Verified from data/video_observations.json and the absence of external sidecars in data/.",
        impact_surface=("parsers", "schema validation", "evaluation"),
    ),
    AssumptionRecord(
        assumption_id="DS-004",
        domain="targets",
        statement="The final delivery supports vehicle, plate visibility, in-cabin object cues, and driver-behavior risk through human-curated clip observations; speed is unavailable.",
        confidence="high",
        verify_when_dataset_arrives="Verified from the delivered media and authoritative video descriptions.",
        impact_surface=("model heads", "UI output", "evaluation"),
    ),
    AssumptionRecord(
        assumption_id="DS-008",
        domain="annotation granularity",
        statement="The final annotation granularity is clip-level human-curated observation, not frame-level structured annotation.",
        confidence="high",
        verify_when_dataset_arrives="Verified from data/video_observations.json.",
        impact_surface=("temporal logic", "metrics", "adapters"),
    ),
    AssumptionRecord(
        assumption_id="DS-010",
        domain="TOGG trigger",
        statement="The observed videos all center on the target TOGG vehicle approaching the camera, and trigger logic can rely on authoritative clip observations when model output is unavailable.",
        confidence="high",
        verify_when_dataset_arrives="Verified from screenshots and user-provided video descriptions.",
        impact_surface=("QoD trigger policy", "critical-event detection"),
    ),
    AssumptionRecord(
        assumption_id="DS-012",
        domain="QoD policy",
        statement="QoD should be triggered only when there is a likely accuracy or clarity gain.",
        confidence="high",
        verify_when_dataset_arrives="Confirm against final API docs and judging guidance.",
        impact_surface=("network orchestration", "simulation"),
    ),
    AssumptionRecord(
        assumption_id="DS-014",
        domain="QoD API integration",
        statement="Real QoD endpoint details remain unavailable, so the repository keeps explicit mock-backed QoD activation behavior.",
        confidence="high",
        verify_when_dataset_arrives="Update only if operator access is separately granted.",
        impact_surface=("API clients", "mobile flow", "backend integration"),
    ),
    AssumptionRecord(
        assumption_id="OR-002",
        domain="orchestration risk labels",
        statement="The current authoritative risk taxonomy is smoking_and_unsafe_scanning, phone_use_while_driving, and drunk_like_erratic_driving.",
        confidence="high",
        verify_when_dataset_arrives="Verified from data/video_observations.json.",
        impact_surface=("mobile output", "reporting", "evaluation"),
    ),
)
