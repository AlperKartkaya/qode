from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _ratio(value: float) -> str:
    return f"{value:.4f}"


def _optional_seconds(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def render_ftr_metrics_markdown(report: dict[str, Any] | str | Path) -> str:
    payload = (
        json.loads(Path(report).read_text(encoding="utf-8"))
        if isinstance(report, (str, Path))
        else report
    )
    vehicle = payload["vehicle"]
    events = payload["events"]
    lines = [
        "# FTR Ground-Truth Evaluation",
        "",
        f"Report version: `{payload['report_version']}`",
        "",
        f"Prediction: `{payload['prediction_path']}`  ",
        f"Ground truth: `{payload['ground_truth_path']}`",
        f"Prediction SHA256: `{payload['prediction_sha256'] or 'in-memory'}`  ",
        f"Ground-truth SHA256: `{payload['ground_truth_sha256'] or 'in-memory'}`",
        "",
        "## Evaluation Boundary",
        "",
        f"Timestamp tolerance: **{events['timestamp_tolerance_seconds']:.3f} seconds**",
        "",
        f"> {events['tolerance_note']}",
        "",
        "## Vehicle Metrics",
        "",
        "| Metric | Result |",
        "| --- | --- |",
        f"| Video ID exact match | {_yes_no(vehicle['video_id_exact_match'])} |",
        f"| Type exact match | {_yes_no(vehicle['type_exact_match'])} |",
        f"| Color exact match | {_yes_no(vehicle['color_exact_match'])} |",
        f"| Plate normalized exact match | {_yes_no(vehicle['plate_normalized_exact_match'])} |",
        f"| Prediction plate regex valid | {_yes_no(vehicle['prediction_plate_regex_valid'])} |",
        f"| Prediction confidence valid | {_yes_no(vehicle['prediction_confidence_range_valid'])} |",
        f"| Vehicle exact-match rate | {_ratio(vehicle['exact_match_rate'])} |",
        "",
        "## Event Summary",
        "",
        "| Scope | TP | FP | FN | Precision | Recall | F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    micro = events["micro"]
    lines.append(
        f"| Micro | {micro['tp']} | {micro['fp']} | {micro['fn']} | "
        f"{_ratio(micro['precision'])} | {_ratio(micro['recall'])} | {_ratio(micro['f1'])} |"
    )
    for family, metric in events["per_family"].items():
        lines.append(
            f"| `{family}` | {metric['tp']} | {metric['fp']} | {metric['fn']} | "
            f"{_ratio(metric['precision'])} | {_ratio(metric['recall'])} | {_ratio(metric['f1'])} |"
        )
    lines.extend(
        [
            "",
            f"Macro precision: **{_ratio(events['macro_precision'])}**  ",
            f"Macro recall: **{_ratio(events['macro_recall'])}**  ",
            f"Macro F1: **{_ratio(events['macro_f1'])}**  ",
            f"Macro scope: {events['macro_scope']}  ",
            "Timestamp MAE: "
            f"**{_optional_seconds(events['timestamp_mae_seconds'])} seconds**",
            "",
            "## Per-Label Metrics",
            "",
            "| Category / label | TP | FP | FN | Precision | Recall | F1 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for label, metric in events["per_label"].items():
        lines.append(
            f"| `{label}` | {metric['tp']} | {metric['fp']} | {metric['fn']} | "
            f"{_ratio(metric['precision'])} | {_ratio(metric['recall'])} | {_ratio(metric['f1'])} |"
        )

    lines.extend(
        [
            "",
            "## Timestamp Sensitivity",
            "",
            "| Tolerance (s) | TP | FP | FN | Precision | Recall | F1 | MAE (s) |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for metric in events["sensitivity"]:
        lines.append(
            f"| {metric['timestamp_tolerance_seconds']:.1f} | {metric['tp']} | "
            f"{metric['fp']} | {metric['fn']} | {_ratio(metric['precision'])} | "
            f"{_ratio(metric['recall'])} | {_ratio(metric['f1'])} | "
            f"{_optional_seconds(metric['timestamp_mae_seconds'])} |"
        )

    lines.extend(["", "## False Positives", ""])
    if events["false_positive_events"]:
        for event in events["false_positive_events"]:
            lines.append(
                f"- `{event['kategori']}:{event['etiket']}` at "
                f"{event['zaman_saniye']:.3f}s (confidence={event['confidence_score']:.4f})"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## False Negatives", ""])
    if events["false_negative_events"]:
        for event in events["false_negative_events"]:
            lines.append(
                f"- `{event['kategori']}:{event['etiket']}` at "
                f"{event['zaman_saniye']:.3f}s (confidence={event['confidence_score']:.4f})"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in payload["limitations"])
    lines.append("")
    return "\n".join(lines)


def export_ftr_metrics_markdown(
    report: dict[str, Any] | str | Path, output_path: str | Path
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_ftr_metrics_markdown(report), encoding="utf-8")
    return target
