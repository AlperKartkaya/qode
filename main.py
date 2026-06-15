"""
main.py — QoDe FTR Competition Entry Point

Reads /app/data/input/video.mp4, runs the full inference pipeline, and writes
/app/data/output/results.json conforming to the FTR output schema.

Local testing: if /app/data/input is absent, falls back to data/ and ./ directories.
"""

import os
import json
import sys
import collections
from pathlib import Path

# Make src importable whether running locally or from /app
sys.path.insert(0, str(Path(__file__).parent / "src"))

import cv2

from smart_road_safety.analysis.model_inference import SceneAnalysisEngine
from smart_road_safety.competition.ftr import (
    FtrCompetitionResult,
    VehicleInfo,
    DetectionEvent,
    write_ftr_result,
)


# ── Constants ─────────────────────────────────────────────────────────────────

# Weights paths (Docker-first, then local dev fallback handled inside engine)
YOLO_WEIGHTS   = "yolo11x.pt"
DRIVER_WEIGHTS = "data/weights/driver_classifier.pt"
VTYPE_WEIGHTS  = "data/weights/vehicle_type_classifier.pt"

# Temporal smoothing: keep a rolling window of N seconds for voting
SMOOTHING_WINDOW_SEC = 3.0

# Minimum confidence to carry a detection event through to the final output
MIN_EVENT_CONF = 0.55


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_video() -> tuple[Path, Path]:
    """Return (video_path, output_dir) — tries Docker paths first, then local."""
    docker_input = Path("/app/data/input")
    docker_output = Path("/app/data/output")

    if docker_input.exists():
        mp4s = [f for f in docker_input.glob("*.mp4") if f.stat().st_size > 0]
        if mp4s:
            docker_output.mkdir(parents=True, exist_ok=True)
            return mp4s[0], docker_output

    # Local dev fallback
    for search_dir in (Path("."), Path("data")):
        mp4s = [f for f in search_dir.glob("*.mp4") if f.stat().st_size > 0]
        if mp4s:
            out = Path("out")
            out.mkdir(exist_ok=True)
            return mp4s[0], out

    raise FileNotFoundError(
        "No valid .mp4 file found in /app/data/input, '.', or 'data/'."
    )


def _mode(items: list) -> object:
    """Return most common item in list, or None if empty."""
    if not items:
        return None
    return collections.Counter(items).most_common(1)[0][0]


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main() -> None:
    # ── Locate video ──────────────────────────────────────────────────────────
    try:
        video_path, output_dir = _find_video()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(f"[QoDe] Processing: {video_path}")

    # ── Initialise inference engine ───────────────────────────────────────────
    engine = SceneAnalysisEngine(
        yolo_model_name=YOLO_WEIGHTS,
        driver_model_path=DRIVER_WEIGHTS,
        vehicle_type_model_path=VTYPE_WEIGHTS,
    )

    # ── Open video ────────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps
    print(f"[QoDe] FPS={fps:.1f}  frames={total_frames}  duration={duration_sec:.1f}s")

    # Sample 1 frame per second (FTR videos are typically ≤10 min = 600 frames)
    frame_step = max(1, int(fps))

    # ── Accumulators ─────────────────────────────────────────────────────────
    vehicle_types:  list[str]   = []
    vehicle_colors: list[str]   = []
    vehicle_confs:  list[float] = []
    plate_votes:    dict[str, int] = {}

    raw_events: list[dict] = []  # all per-frame detections before deduplication

    frame_idx = 0
    processed  = 0

    # ── Frame loop ────────────────────────────────────────────────────────────
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_step == 0:
            ts = frame_idx / fps
            analysis = engine.analyze_frame(frame, ts)
            processed += 1

            if analysis["vehicle_detected"]:
                vehicle_types.append(analysis["vehicle_type"])
                vehicle_colors.append(analysis["vehicle_color"])
                vehicle_confs.append(analysis["vehicle_confidence"])
                if analysis["plate_text"]:
                    p = analysis["plate_text"]
                    plate_votes[p] = plate_votes.get(p, 0) + 1

            for ev in analysis["driver_events"]:
                if ev["confidence_score"] >= MIN_EVENT_CONF:
                    raw_events.append(ev)

        frame_idx += 1

    cap.release()
    print(f"[QoDe] Processed {processed} frames.")

    # ── Temporal smoothing & deduplication ───────────────────────────────────
    # Group events by (kategori, etiket) and deduplicate within SMOOTHING_WINDOW_SEC.
    # Only keep one event per label per time window to avoid flooding the output.
    deduplicated: list[dict] = []
    last_seen: dict[tuple, float] = {}

    for ev in sorted(raw_events, key=lambda e: e["zaman_saniye"]):
        key = (ev["kategori"], ev["etiket"])
        last_ts = last_seen.get(key, -999.0)
        if ev["zaman_saniye"] - last_ts >= SMOOTHING_WINDOW_SEC:
            deduplicated.append(ev)
            last_seen[key] = ev["zaman_saniye"]

    # ── Build final vehicle info ───────────────────────────────────────────────
    final_type  = _mode(vehicle_types)  or "sedan"
    final_color = _mode(vehicle_colors) or "beyaz"
    final_conf  = (sum(vehicle_confs) / len(vehicle_confs)) if vehicle_confs else 0.80
    final_plate = max(plate_votes, key=plate_votes.get) if plate_votes else "tespit_edilemedi"

    vehicle_info = VehicleInfo(
        tip=final_type,
        plaka=final_plate,
        renk=final_color,
        confidence_score=round(final_conf, 4),
    )

    ftr_result = FtrCompetitionResult(
        video_id=video_path.name,
        arac_bilgisi=vehicle_info,
        tespitler=tuple(
            DetectionEvent(
                zaman_saniye=ev["zaman_saniye"],
                kategori=ev["kategori"],
                etiket=ev["etiket"],
                confidence_score=ev["confidence_score"],
            )
            for ev in deduplicated
        ),
    )

    out_file = output_dir / "results.json"
    write_ftr_result(ftr_result, out_file)
    print(f"[QoDe] results.json saved → {out_file}")
    print(f"[QoDe] Vehicle: {final_type} / {final_color} / {final_plate} (conf={final_conf:.2f})")
    print(f"[QoDe] Events:  {len(deduplicated)} unique detection(s)")


if __name__ == "__main__":
    main()
