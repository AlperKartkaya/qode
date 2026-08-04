from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from ..competition import (
    DETECTION_LABELS_BY_CATEGORY,
    PLATE_PATTERN,
    DetectionEvent,
    FtrCompetitionResult,
    read_ftr_result,
)

DEFAULT_SENSITIVITY_TOLERANCES: tuple[float, ...] = (0.5, 1.0, 2.0, 3.0)
DEVELOPMENT_TOLERANCE_NOTE = (
    "Timestamp tolerance is a development calibration parameter, not an official "
    "competition matching rule."
)


@dataclass(frozen=True)
class CountMetrics:
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class VehicleMetrics:
    video_id_exact_match: bool
    type_exact_match: bool
    color_exact_match: bool
    plate_normalized_exact_match: bool
    prediction_plate_regex_valid: bool
    prediction_confidence_range_valid: bool
    exact_match_rate: float


@dataclass(frozen=True)
class MatchedEvent:
    kategori: str
    etiket: str
    prediction_zaman_saniye: float
    ground_truth_zaman_saniye: float
    absolute_error_seconds: float
    prediction_confidence_score: float
    ground_truth_confidence_score: float


@dataclass(frozen=True)
class UnmatchedEvent:
    zaman_saniye: float
    kategori: str
    etiket: str
    confidence_score: float


@dataclass(frozen=True)
class SensitivityMetrics:
    timestamp_tolerance_seconds: float
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    timestamp_mae_seconds: float | None


@dataclass(frozen=True)
class FtrEventMetrics:
    timestamp_tolerance_seconds: float
    tolerance_note: str
    per_label: dict[str, CountMetrics]
    per_family: dict[str, CountMetrics]
    micro: CountMetrics
    macro_precision: float
    macro_recall: float
    macro_f1: float
    macro_scope: str
    timestamp_mae_seconds: float | None
    matched_events: tuple[MatchedEvent, ...]
    false_positive_events: tuple[UnmatchedEvent, ...]
    false_negative_events: tuple[UnmatchedEvent, ...]
    sensitivity: tuple[SensitivityMetrics, ...]


@dataclass(frozen=True)
class FtrEvaluationReport:
    report_version: str
    prediction_path: str
    ground_truth_path: str
    prediction_sha256: str | None
    ground_truth_sha256: str | None
    prediction_video_id: str
    ground_truth_video_id: str
    vehicle: VehicleMetrics
    events: FtrEventMetrics
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _counts(tp: int, fp: int, fn: int) -> CountMetrics:
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = (
        0.0
        if precision + recall == 0.0
        else 2.0 * precision * recall / (precision + recall)
    )
    return CountMetrics(tp=tp, fp=fp, fn=fn, precision=precision, recall=recall, f1=f1)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mean(values: Iterable[float]) -> float:
    materialized = tuple(values)
    return 0.0 if not materialized else sum(materialized) / len(materialized)


def _event_sort_key(event: DetectionEvent) -> tuple[float, str, str, float]:
    return (
        event.zaman_saniye,
        event.kategori,
        event.etiket,
        event.confidence_score,
    )


def _plan_rank(
    plan: tuple[tuple[int, int, float], ...],
) -> tuple[int, float, tuple[tuple[int, int], ...]]:
    return (
        -len(plan),
        round(sum(item[2] for item in plan), 12),
        tuple((item[0], item[1]) for item in plan),
    )


def _match_group(
    predictions: tuple[DetectionEvent, ...],
    ground_truth: tuple[DetectionEvent, ...],
    tolerance: float,
) -> tuple[tuple[int, int, float], ...]:
    """Return a maximum-cardinality, minimum-error one-to-one assignment."""

    @lru_cache(maxsize=None)
    def solve(prediction_index: int, ground_truth_index: int):
        if prediction_index == len(predictions) or ground_truth_index == len(ground_truth):
            return ()

        candidates = [
            solve(prediction_index + 1, ground_truth_index),
            solve(prediction_index, ground_truth_index + 1),
        ]
        difference = abs(
            predictions[prediction_index].zaman_saniye
            - ground_truth[ground_truth_index].zaman_saniye
        )
        if difference <= tolerance + 1e-12:
            candidates.append(
                (
                    (prediction_index, ground_truth_index, difference),
                    *solve(prediction_index + 1, ground_truth_index + 1),
                )
            )
        return min(candidates, key=_plan_rank)

    return solve(0, 0)


def _event_groups(
    events: tuple[DetectionEvent, ...],
) -> dict[tuple[str, str], tuple[DetectionEvent, ...]]:
    groups: dict[tuple[str, str], list[DetectionEvent]] = {}
    for event in events:
        groups.setdefault((event.kategori, event.etiket), []).append(event)
    return {
        key: tuple(sorted(values, key=_event_sort_key)) for key, values in groups.items()
    }


def _unmatched(event: DetectionEvent) -> UnmatchedEvent:
    return UnmatchedEvent(
        zaman_saniye=event.zaman_saniye,
        kategori=event.kategori,
        etiket=event.etiket,
        confidence_score=event.confidence_score,
    )


def _evaluate_event_core(
    prediction: FtrCompetitionResult,
    ground_truth: FtrCompetitionResult,
    tolerance: float,
) -> tuple[
    dict[str, CountMetrics],
    dict[str, CountMetrics],
    CountMetrics,
    float,
    float,
    float,
    float | None,
    tuple[MatchedEvent, ...],
    tuple[UnmatchedEvent, ...],
    tuple[UnmatchedEvent, ...],
]:
    prediction_groups = _event_groups(prediction.tespitler)
    ground_truth_groups = _event_groups(ground_truth.tespitler)
    all_labels = tuple(
        (category, label)
        for category, labels in sorted(DETECTION_LABELS_BY_CATEGORY.items())
        for label in labels
    )

    per_label: dict[str, CountMetrics] = {}
    matched_events: list[MatchedEvent] = []
    false_positives: list[UnmatchedEvent] = []
    false_negatives: list[UnmatchedEvent] = []

    for category, label in all_labels:
        predicted = prediction_groups.get((category, label), ())
        expected = ground_truth_groups.get((category, label), ())
        pairs = _match_group(predicted, expected, tolerance)
        matched_prediction = {item[0] for item in pairs}
        matched_ground_truth = {item[1] for item in pairs}
        per_label[f"{category}:{label}"] = _counts(
            tp=len(pairs),
            fp=len(predicted) - len(pairs),
            fn=len(expected) - len(pairs),
        )
        for prediction_index, ground_truth_index, difference in pairs:
            predicted_event = predicted[prediction_index]
            expected_event = expected[ground_truth_index]
            matched_events.append(
                MatchedEvent(
                    kategori=category,
                    etiket=label,
                    prediction_zaman_saniye=predicted_event.zaman_saniye,
                    ground_truth_zaman_saniye=expected_event.zaman_saniye,
                    absolute_error_seconds=difference,
                    prediction_confidence_score=predicted_event.confidence_score,
                    ground_truth_confidence_score=expected_event.confidence_score,
                )
            )
        false_positives.extend(
            _unmatched(event)
            for index, event in enumerate(predicted)
            if index not in matched_prediction
        )
        false_negatives.extend(
            _unmatched(event)
            for index, event in enumerate(expected)
            if index not in matched_ground_truth
        )

    per_family: dict[str, CountMetrics] = {}
    for category, labels in sorted(DETECTION_LABELS_BY_CATEGORY.items()):
        label_metrics = [per_label[f"{category}:{label}"] for label in labels]
        per_family[category] = _counts(
            tp=sum(item.tp for item in label_metrics),
            fp=sum(item.fp for item in label_metrics),
            fn=sum(item.fn for item in label_metrics),
        )

    micro = _counts(
        tp=sum(item.tp for item in per_family.values()),
        fp=sum(item.fp for item in per_family.values()),
        fn=sum(item.fn for item in per_family.values()),
    )
    active_labels = [
        item for item in per_label.values() if item.tp + item.fp + item.fn > 0
    ]
    timestamp_mae = (
        None
        if not matched_events
        else _mean(item.absolute_error_seconds for item in matched_events)
    )
    matched_events.sort(
        key=lambda item: (
            item.kategori,
            item.etiket,
            item.ground_truth_zaman_saniye,
            item.prediction_zaman_saniye,
        )
    )
    false_positives.sort(
        key=lambda item: (item.kategori, item.etiket, item.zaman_saniye)
    )
    false_negatives.sort(
        key=lambda item: (item.kategori, item.etiket, item.zaman_saniye)
    )
    return (
        per_label,
        per_family,
        micro,
        _mean(item.precision for item in active_labels),
        _mean(item.recall for item in active_labels),
        _mean(item.f1 for item in active_labels),
        timestamp_mae,
        tuple(matched_events),
        tuple(false_positives),
        tuple(false_negatives),
    )


def evaluate_ftr_results(
    prediction: FtrCompetitionResult,
    ground_truth: FtrCompetitionResult,
    timestamp_tolerance_seconds: float = 1.0,
    *,
    prediction_path: str = "<memory>",
    ground_truth_path: str = "<memory>",
    prediction_sha256: str | None = None,
    ground_truth_sha256: str | None = None,
) -> FtrEvaluationReport:
    if (
        not math.isfinite(timestamp_tolerance_seconds)
        or timestamp_tolerance_seconds < 0
    ):
        raise ValueError(
            "timestamp_tolerance_seconds must be finite and non-negative."
        )

    vehicle_checks = (
        prediction.arac_bilgisi.tip == ground_truth.arac_bilgisi.tip,
        prediction.arac_bilgisi.renk == ground_truth.arac_bilgisi.renk,
        prediction.arac_bilgisi.plaka == ground_truth.arac_bilgisi.plaka,
    )
    vehicle = VehicleMetrics(
        video_id_exact_match=prediction.video_id == ground_truth.video_id,
        type_exact_match=vehicle_checks[0],
        color_exact_match=vehicle_checks[1],
        plate_normalized_exact_match=vehicle_checks[2],
        prediction_plate_regex_valid=bool(
            PLATE_PATTERN.fullmatch(prediction.arac_bilgisi.plaka)
        ),
        prediction_confidence_range_valid=(
            0.0 <= prediction.arac_bilgisi.confidence_score <= 1.0
        ),
        exact_match_rate=_mean(1.0 if value else 0.0 for value in vehicle_checks),
    )

    core = _evaluate_event_core(
        prediction, ground_truth, timestamp_tolerance_seconds
    )
    sensitivity: list[SensitivityMetrics] = []
    for tolerance in DEFAULT_SENSITIVITY_TOLERANCES:
        sensitivity_core = _evaluate_event_core(prediction, ground_truth, tolerance)
        metric = sensitivity_core[2]
        sensitivity.append(
            SensitivityMetrics(
                timestamp_tolerance_seconds=tolerance,
                tp=metric.tp,
                fp=metric.fp,
                fn=metric.fn,
                precision=metric.precision,
                recall=metric.recall,
                f1=metric.f1,
                timestamp_mae_seconds=sensitivity_core[6],
            )
        )

    events = FtrEventMetrics(
        timestamp_tolerance_seconds=timestamp_tolerance_seconds,
        tolerance_note=DEVELOPMENT_TOLERANCE_NOTE,
        per_label=core[0],
        per_family=core[1],
        micro=core[2],
        macro_precision=core[3],
        macro_recall=core[4],
        macro_f1=core[5],
        macro_scope="labels with at least one prediction or ground-truth event",
        timestamp_mae_seconds=core[6],
        matched_events=core[7],
        false_positive_events=core[8],
        false_negative_events=core[9],
        sensitivity=tuple(sensitivity),
    )
    return FtrEvaluationReport(
        report_version="ftr-metrics-v1",
        prediction_path=prediction_path,
        ground_truth_path=ground_truth_path,
        prediction_sha256=prediction_sha256,
        ground_truth_sha256=ground_truth_sha256,
        prediction_video_id=prediction.video_id,
        ground_truth_video_id=ground_truth.video_id,
        vehicle=vehicle,
        events=events,
        limitations=(
            DEVELOPMENT_TOLERANCE_NOTE,
            "Faz 2 is a single development clip and does not prove hidden-final generalization.",
        ),
    )


def evaluate_ftr_files(
    prediction_path: str | Path,
    ground_truth_path: str | Path,
    timestamp_tolerance_seconds: float = 1.0,
) -> FtrEvaluationReport:
    prediction_file = Path(prediction_path)
    ground_truth_file = Path(ground_truth_path)
    prediction = read_ftr_result(prediction_file)
    ground_truth = read_ftr_result(ground_truth_file)
    return evaluate_ftr_results(
        prediction,
        ground_truth,
        timestamp_tolerance_seconds,
        prediction_path=str(prediction_file),
        ground_truth_path=str(ground_truth_file),
        prediction_sha256=_sha256(prediction_file),
        ground_truth_sha256=_sha256(ground_truth_file),
    )


def write_ftr_evaluation_report(
    report: FtrEvaluationReport, output_path: str | Path
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target
