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
        statement="The offline dataset will primarily contain video files.",
        confidence="high",
        verify_when_dataset_arrives="Inspect the top-level tree and file extensions.",
        impact_surface=("ingestion", "batching", "preprocessing"),
    ),
    AssumptionRecord(
        assumption_id="DS-002",
        domain="sample unit",
        statement="The main sample unit will be a video clip or stream segment.",
        confidence="high",
        verify_when_dataset_arrives="Inspect sample identifiers and annotation keys.",
        impact_surface=("dataset adapters", "evaluation"),
    ),
    AssumptionRecord(
        assumption_id="DS-004",
        domain="targets",
        statement="The dataset will support vehicle, plate, speed, in-cabin, and driver-behavior related outputs.",
        confidence="high",
        verify_when_dataset_arrives="Compare the released label ontology to the expected target families.",
        impact_surface=("model heads", "UI output", "evaluation"),
    ),
    AssumptionRecord(
        assumption_id="DS-008",
        domain="annotation granularity",
        statement="Some labels may be frame-level while others may be clip-level or event-level.",
        confidence="medium",
        verify_when_dataset_arrives="Inspect representative labels from each target family.",
        impact_surface=("temporal logic", "metrics", "adapters"),
    ),
    AssumptionRecord(
        assumption_id="DS-010",
        domain="TOGG trigger",
        statement="The exact representation of TOGG approach is unknown and must remain configurable.",
        confidence="high",
        verify_when_dataset_arrives="Inspect labels and any target-vehicle metadata.",
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
        statement="Current work should model QoD intent and state transitions, not final HTTP payloads.",
        confidence="high",
        verify_when_dataset_arrives="Read the official endpoint and auth documentation.",
        impact_surface=("API clients", "mobile flow", "backend integration"),
    ),
)
